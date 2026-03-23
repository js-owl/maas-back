"""Message processor for Bitrix24 async queue."""
from __future__ import annotations

import json
from typing import Any
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.bitrix24.async_queue.idempotency import (
    check_idempotency,
    store_idempotency_token,
)
from backend.bitrix24.async_queue.message import QueueMessage, validate_message_fields
from backend.bitrix24.async_queue.routing import ENTITY_TYPE_ROUTING
from backend.bitrix24.client import BitrixClient
from backend.bitrix24.constants import OwnerType
from backend.bitrix24.dto.product_row import ProductRowCreate
from backend.bitrix24.product_property_value_ids import extract_property_value_ids
from backend.bitrix24.repositories.mapping_repository import get_bitrix_id, upsert_mapping
from backend.bitrix24.services.product import ProductService
from backend.bitrix24.services.product_row import ProductRowService
from backend.bitrix24.services.deal import DealService
from backend.bitrix24.funnel_cache import get_or_create_deal_category_id, resolve_stage_id
from backend.calculations.proxy import get_locations
from backend.database import AsyncSessionLocal
from backend.models import Kit, Order
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class ProcessingError(Exception):
    """Wrap processing failures with idempotency context."""

    def __init__(self, message: str, *, cause: Exception, idempotency_claimed: bool) -> None:
        super().__init__(message)
        self.cause = cause
        self.idempotency_claimed = idempotency_claimed


def _extract_bitrix_id(result: Any) -> int | str | None:
    if result is None:
        return None
    if isinstance(result, dict):
        if "id" in result:
            return result["id"]
        if "ID" in result:
            return result["ID"]
    if isinstance(result, (int, str)):
        return result
    return None


async def _resolve_location_label(location_id: Any) -> str | None:
    """Resolve location external id to label via calculator proxy get_locations()."""
    if location_id is None:
        return None
    try:
        resp = await get_locations()
        locations = []
        if isinstance(resp, dict):
            locations = resp.get("locations") or []
        elif isinstance(resp, list):
            locations = resp
        key = str(location_id)
        for item in locations:
            if not isinstance(item, dict):
                continue
            if str(item.get("id")) == key:
                # return (item.get("label") or item.get("name") or "").strip() or None
                return item.get("label").strip() or None
    except Exception as e:
        logger.warning("Failed to resolve location label for %s: %s", location_id, e)
    return None


async def _sync_deal_product_rows(
    client: BitrixClient,
    deal_bitrix_id: int,
    kit_id: int,
) -> None:
    """After deal create/update: set deal product rows from kit orders (PRICE, QUANTITY, DISCOUNT_RATE)."""
    rows: list[ProductRowCreate] = []
    async with AsyncSessionLocal() as db:
        kit = await db.get(Kit, kit_id)
        if not kit:
            logger.warning("Kit %s not found for deal product rows sync", kit_id)
            return
        try:
            order_ids = json.loads(getattr(kit, "order_ids", "[]") or "[]")
        except (TypeError, ValueError):
            order_ids = []
        res = await db.execute(select(Order).where(Order.order_id.in_(order_ids)))
        orders = res.scalars().all()
        for order in orders:
            product_bitrix_id = await get_bitrix_id(db, order.order_id, "product")
            if product_bitrix_id is None:
                logger.debug(
                    "Skipping product row for order %s: no product mapping yet",
                    order.order_id,
                )
                continue
            price = getattr(order, "detail_price_one", None)
            quantity = getattr(order, "quantity", None) or 0
            k_q = getattr(order, "k_quantity", None)
            discount_rate = round((1.0 - float(k_q)) * 100.0, 2) if k_q is not None else None
            rows.append(
                ProductRowCreate(
                    ownerId=deal_bitrix_id,
                    ownerType=OwnerType.DEAL,
                    productId=int(product_bitrix_id),
                    price=float(price) if price is not None else None,
                    quantity=float(quantity),
                    discountRate=discount_rate,
                )
            )
    if not rows:
        logger.debug("No product rows to set for deal %s (kit_id=%s)", deal_bitrix_id, kit_id)
        return
    product_row_svc = ProductRowService(client)
    await product_row_svc.set(OwnerType.DEAL, deal_bitrix_id, rows)


async def _kit_ids_containing_order(db: AsyncSession, order_id: int) -> list[int]:
    """Return kit_ids whose order_ids list contains the given order_id."""
    result = await db.execute(select(Kit.kit_id, Kit.order_ids))
    rows = result.all()
    out: list[int] = []
    for (kit_id, order_ids_str) in rows:
        if not order_ids_str:
            continue
        try:
            ids = json.loads(order_ids_str)
            if isinstance(ids, list) and order_id in [int(x) for x in ids]:
                out.append(kit_id)
        except (TypeError, ValueError):
            continue
    return out


def get_service_instance(
    entity_type: str,
    client: BitrixClient,
    payload: dict[str, Any] | None,
    cache: dict[tuple[str, str | None], Any],
) -> Any:
    """Instantiate Bitrix24 service using routing table."""
    entry = ENTITY_TYPE_ROUTING[entity_type]
    service_cls = entry["service"]
    payload = payload or {}

    if entity_type == "userfield":
        entity = payload.get("entity")
        if not entity:
            raise ValueError("payload must include entity for userfield operations")
        cache_key = (entity_type, str(entity))
        if cache_key not in cache:
            cache[cache_key] = service_cls(client, entity=entity)
        return cache[cache_key]

    cache_key = (entity_type, None)
    if cache_key not in cache:
        cache[cache_key] = service_cls(client)
    return cache[cache_key]


async def process_message(
    message: QueueMessage,
    client: BitrixClient,
    redis,
    services_cache: dict[tuple[str, str | None], Any],
) -> Any:
    """Route and process a single queue message."""
    idempotency_claimed = False
    try:
        validate_message_fields(message)
        if message.entity_type not in ENTITY_TYPE_ROUTING:
            raise ValueError(f"Unknown entity_type: {message.entity_type}")

        entry = ENTITY_TYPE_ROUTING[message.entity_type]
        action_map = entry["actions"]
        if message.action not in action_map:
            raise ValueError(f"Unsupported action: {message.action}")

        payload = message.payload or {}
        # --- Deal funnel/category routing + stage name->code mapping ---
        if message.entity_type == "deal" and message.action in {"create", "update"}:
            async with AsyncSessionLocal() as _db:
                # Determine CATEGORY_ID
                category_id: int | None = None
                if message.action == "create":
                    if message.local_id is not None:
                        kit = await _db.get(Kit, message.local_id)
                        if kit is not None:
                            loc_label = await _resolve_location_label(getattr(kit, "location", None))
                            try:
                                category_id = await get_or_create_deal_category_id(_db, client, category_name=loc_label)
                                payload["CATEGORY_ID"] = category_id
                            except Exception as e:
                                logger.warning("Failed to resolve/create deal category for location %s: %s", loc_label, e)
                else:
                    # update: category is immutable; read existing deal to know its category
                    deal_id = message.external_id
                    if deal_id is None and message.local_id is not None:
                        deal_id = await get_bitrix_id(_db, message.local_id, "deal")
                    if deal_id is not None:
                        try:
                            deal_service = DealService(client)
                            deal_obj = await deal_service.get(int(deal_id))
                            data = deal_obj.to_dict()
                            cid = data.get("CATEGORY_ID")
                            category_id = int(cid) if cid is not None else None
                        except Exception as e:
                            logger.warning("Failed to read deal %s to resolve CATEGORY_ID: %s", deal_id, e)

                # Translate STAGE_ID if payload carries a human-readable name
                stage_val = payload.get("STAGE_ID")
                if stage_val is not None and category_id is not None:
                    try:
                        mapped = await resolve_stage_id(_db, stage_name=str(stage_val), category_id=category_id)
                        if mapped is not None:
                            payload["STAGE_ID"] = mapped
                    except Exception as e:
                        logger.warning("Failed to map stage name '%s' to code for category %s: %s", stage_val, category_id, e)

        dto_map = entry.get("dto", {})
        dto_cls = dto_map.get(message.action)
        fields = dto_cls.model_validate(payload) if dto_cls else None

        if message.action == "create":
            if message.local_id is None:
                raise ValueError("local_id is required for create operations")
            idempotency_claimed = await check_idempotency(
                redis, message.entity_type, message.local_id
            )
            if not idempotency_claimed:
                logger.info(
                    "Skipping duplicate create for %s:%s",
                    message.entity_type,
                    message.local_id,
                )
                return None

        service = get_service_instance(
            message.entity_type, client, payload, services_cache
        )
        method_name = action_map[message.action]

        if message.entity_type == "category":
            entity_type_id = payload.get("entity_type_id")
            if entity_type_id is None:
                raise ValueError("payload must include entity_type_id")
            if message.action == "create":
                result = await getattr(service, method_name)(entity_type_id, fields)
            elif message.action == "update":
                result = await getattr(service, method_name)(
                    entity_type_id, message.external_id, fields
                )
            else:
                result = await getattr(service, method_name)(
                    entity_type_id, message.external_id
                )
        else:
            if message.action == "create":
                result = await getattr(service, method_name)(fields)
            elif message.action == "update":
                result = await getattr(service, method_name)(message.external_id, fields)
            else:
                result = await getattr(service, method_name)(message.external_id)

        if message.action == "create" and idempotency_claimed:
            bitrix_id = _extract_bitrix_id(result)
            if bitrix_id is not None:
                await store_idempotency_token(
                    redis, message.entity_type, message.local_id, bitrix_id
                )
                
                # Store mapping in database
                try:
                    async with AsyncSessionLocal() as db:
                        await upsert_mapping(
                            db=db,
                            maas_id=message.local_id,
                            bitrix_id=int(bitrix_id) if isinstance(bitrix_id, str) else bitrix_id,
                            entity_type=message.entity_type
                        )
                        logger.info(
                            "Created mapping: %s MaaS ID %s <-> Bitrix ID %s",
                            message.entity_type,
                            message.local_id,
                            bitrix_id
                        )
                except Exception as mapping_error:
                    # Log error but don't fail the entire operation
                    # since the Bitrix operation already succeeded
                    logger.error(
                        "Failed to create mapping for %s:%s -> %s: %s",
                        message.entity_type,
                        message.local_id,
                        bitrix_id,
                        mapping_error,
                        exc_info=True
                    )

        if (
            message.entity_type == "product"
            and message.local_id is not None
            and message.action in ("create", "update")
        ):
            product_bitrix_id = (
                _extract_bitrix_id(result) if message.action == "create" else message.external_id
            )
            if product_bitrix_id is not None:
                try:
                    product_svc = get_service_instance(
                        "product", client, payload, services_cache
                    )
                    product = await product_svc.get(int(product_bitrix_id))
                    property_buffer = extract_property_value_ids(product.to_dict())
                    if property_buffer:
                        async with AsyncSessionLocal() as db:
                            await upsert_mapping(
                                db=db,
                                maas_id=message.local_id,
                                bitrix_id=int(product_bitrix_id),
                                entity_type="product",
                                buffer=property_buffer,
                                merge_buffer=True,
                            )
                        logger.debug(
                            "Stored product property valueIds in mapping buffer for order_id=%s",
                            message.local_id,
                        )
                except Exception as prop_err:
                    logger.warning(
                        "Failed to store product property valueIds for order_id=%s: %s",
                        message.local_id,
                        prop_err,
                        exc_info=True,
                    )
                # Sync deal product rows only when updating a product (not on create)
                if message.action == "update":
                    try:
                        async with AsyncSessionLocal() as db:
                            kit_ids = await _kit_ids_containing_order(db, message.local_id)
                            for k_id in kit_ids:
                                deal_bitrix_id = await get_bitrix_id(db, k_id, "deal")
                                if deal_bitrix_id is not None:
                                    await _sync_deal_product_rows(
                                        client, int(deal_bitrix_id), k_id
                                    )
                    except Exception as row_err:
                        logger.warning(
                            "Deal product rows sync after product update failed for order_id=%s: %s",
                            message.local_id,
                            row_err,
                            exc_info=True,
                        )
        elif (
            message.entity_type == "deal"
            and message.local_id is not None
            and message.action in ("create", "update")
        ):
            # After deal create or update: sync deal product rows for that kit
            deal_bitrix_id = (
                _extract_bitrix_id(result) if message.action == "create" else message.external_id
            )
            if deal_bitrix_id is not None:
                try:
                    await _sync_deal_product_rows(
                        client, int(deal_bitrix_id), message.local_id
                    )
                except Exception as row_err:
                    logger.warning(
                        "Deal product rows sync failed for kit_id=%s: %s",
                        message.local_id,
                        row_err,
                        exc_info=True,
                    )
        return result
    except Exception as exc:
        raise ProcessingError(
            "Failed to process message",
            cause=exc,
            idempotency_claimed=idempotency_claimed,
        ) from exc


__all__ = ["ProcessingError", "get_service_instance", "process_message"]
