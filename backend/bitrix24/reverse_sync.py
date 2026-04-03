"""Reverse sync from Bitrix24 to MaaS: timestamp storage and sync job."""

from __future__ import annotations

from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend import schemas
from backend.bitrix24.client import BitrixClient
from backend.bitrix24.constants import OwnerType
from backend.bitrix24.dto.contact import Contact
from backend.bitrix24.dto.deal import Deal
from backend.bitrix24.dto.product import Product
from backend.bitrix24.repositories.mapping_repository import get_maas_id
from backend.bitrix24.services.contact import ContactService
from backend.bitrix24.services.deal import DealService
from backend.bitrix24.services.product import ProductService
from backend.bitrix24.services.product_row import ProductRowService
from backend.bitrix24.sync_payload import (
    contact_to_user_update,
    deal_to_kit_update,
    product_to_order_update,
    parse_breakdown_from_order,
)
from backend.kits import repository as kits_repo
from backend.orders import repository as orders_repo
from backend.users import repository as users_repo
from backend.utils.logging import get_logger

logger = get_logger(__name__)

REVERSE_SYNC_KEY_PREFIX = "bitrix:reverse_sync:"
ENTITY_TYPES = ("contact", "deal", "product")
LIST_PAGE_SIZE = 50


def _key(entity_type: str) -> str:
    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"entity_type must be one of {ENTITY_TYPES}, got {entity_type!r}")
    return f"{REVERSE_SYNC_KEY_PREFIX}{entity_type}"


async def get_last_sync_ts(redis: Redis, entity_type: str) -> str | None:
    """Return the last sync timestamp for the given entity type (ISO string), or None if never run."""
    val = await redis.get(_key(entity_type))
    if val is None:
        return None
    return val.decode("utf-8") if isinstance(val, bytes) else str(val)


async def set_last_sync_ts(redis: Redis, entity_type: str, ts: str) -> None:
    """Store the last sync timestamp (ISO string) for the given entity type."""
    await redis.set(_key(entity_type), ts)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_sync_ts_for_filter(redis: Redis, entity_type: str) -> str:
    """Return timestamp to use as filter for list API: last sync ts if present, else current time (ISO).
    Using current time when no previous run means the first run will list nothing (no historical pull).
    """
    last = await get_last_sync_ts(redis, entity_type)
    return last if last else _now_iso()


async def list_modified_contact_ids(client: BitrixClient, filter_ts: str) -> list[int]:
    """List contact IDs from Bitrix with filter >DATE_MODIFY = filter_ts, with pagination."""
    svc = ContactService(client)
    out: list[int] = []
    start = 0
    while True:
        page = await svc.list(
            filter={">DATE_MODIFY": filter_ts},
            start=start,
        )
        for c in page:
            id_val = getattr(c, "ID", None)
            if id_val is not None:
                out.append(int(id_val))
        if len(page) < LIST_PAGE_SIZE:
            break
        start += len(page)
    return out


async def list_modified_deal_ids(client: BitrixClient, filter_ts: str) -> list[int]:
    """List deal IDs from Bitrix with filter >DATE_MODIFY = filter_ts, with pagination."""
    svc = DealService(client)
    out: list[int] = []
    start = 0
    while True:
        page = await svc.list(
            filter={">DATE_MODIFY": filter_ts},
            start=start,
        )
        for d in page:
            id_val = getattr(d, "ID", None)
            if id_val is not None:
                out.append(int(id_val))
        if len(page) < LIST_PAGE_SIZE:
            break
        start += len(page)
    return out


async def list_modified_product_ids(client: BitrixClient, filter_ts: str) -> list[int]:
    """List product IDs from Bitrix with filter >timestampX = filter_ts, with pagination."""
    svc = ProductService(client)
    out: list[int] = []
    start = 0
    while True:
        page = await svc.list(
            select=["id", "iblockId"],
            filter={">timestampX": filter_ts, "iblockId": 14},
            start=start,
        )
        for p in page:
            id_val = getattr(p, "id", None)
            if id_val is not None:
                out.append(int(id_val))
        if len(page) < LIST_PAGE_SIZE:
            break
        start += len(page)
    return out


def _is_create_only_contact(contact: Contact) -> bool:
    dc = getattr(contact, "DATE_CREATE", None)
    dm = getattr(contact, "DATE_MODIFY", None)
    return bool(dc and dm and dc == dm)


def _is_create_only_deal(deal: Deal) -> bool:
    dc = getattr(deal, "DATE_CREATE", None)
    dm = getattr(deal, "DATE_MODIFY", None)
    return bool(dc and dm and dc == dm)


def _is_create_only_product(product: Product) -> bool:
    dc = getattr(product, "dateCreate", None)
    ts = getattr(product, "timestampX", None)
    return bool(dc and ts and dc == ts)


async def run_contact_sync(
    client: BitrixClient,
    redis: Redis,
    db: AsyncSession,
) -> None:
    """Users are one-way synced from MaaS to Bitrix; Bitrix contact edits must not modify MaaS users."""
    ts = _now_iso()
    await set_last_sync_ts(redis, "contact", ts)
    logger.info("Reverse sync for Bitrix contacts is disabled: MaaS service is the source of truth for users")


async def run_product_sync(
    client: BitrixClient,
    redis: Redis,
    db: AsyncSession,
) -> None:
    """List modified products, resolve to MaaS orders, skip create-only, apply updates. Persist timestamp after run."""
    filter_ts = await get_sync_ts_for_filter(redis, "product")
    bitrix_ids = await list_modified_product_ids(client, filter_ts)
    filter_ts = _now_iso()
    product_svc = ProductService(client)
    for bitrix_id in bitrix_ids:
        maas_id = await get_maas_id(db, bitrix_id, "product")
        if maas_id is None:
            continue
        try:
            product = await product_svc.get(bitrix_id)
            if _is_create_only_product(product):
                continue
            current_order = await orders_repo.get_order_by_id(db, maas_id)
            current_breakdown = (
                parse_breakdown_from_order(current_order) if current_order else None
            )
            payload = await product_to_order_update(
                db, product, current_breakdown=current_breakdown
            )
            if not payload:
                continue
            await orders_repo.update_order(db, maas_id, schemas.OrderUpdate(**payload))
        except Exception as exc:
            logger.warning("Reverse sync product bitrix_id=%s maas_id=%s failed: %s", bitrix_id, maas_id, exc, exc_info=True)
    await set_last_sync_ts(redis, "product", filter_ts)


def _row_to_order_attrs(row: object) -> dict:
    """Extract price, quantity, discountRate from a product row for reverse sync to order.
    Returns: detail_price_one (default 0.00), detail_price = detail_price_one * k_quantity,
    quantity (default 1), k_quantity (default 1.00), total_price = detail_price_one * quantity * k_quantity.
    """
    price = getattr(row, "price", None)
    quantity = getattr(row, "quantity", None)
    discount_rate = getattr(row, "discountRate", None)
    # k_quantity = 1 - discountRate/100 (inverse of processor: discount_rate = (1 - k_q) * 100)
    k_quantity = (
        round(1.0 - float(discount_rate) / 100.0, 6)
        if discount_rate is not None
        else 1.00
    )
    detail_price_one = float(price) if price is not None else 0.00
    qty = int(quantity) if quantity is not None else 1
    detail_price = round(detail_price_one * k_quantity, 2)
    total_price = round(detail_price_one * qty * k_quantity, 2)
    return {
        "detail_price_one": detail_price_one,
        "detail_price": detail_price,
        "quantity": qty,
        "k_quantity": k_quantity,
        "total_price": total_price,
    }


async def _deal_product_rows_with_order_attrs(
    client: BitrixClient,
    db: AsyncSession,
    deal_bitrix_id: int,
) -> list[tuple[int, dict]]:
    """Fetch deal product rows and resolve productId to MaaS order_id with row attributes.
    Returns list of (order_id, order_attrs) in row order for reverse sync (price, quantity, discount → orders).
    Skip rows with no product→order mapping.
    """
    row_svc = ProductRowService(client)
    rows = await row_svc.list(
        filter={"=ownerType": OwnerType.DEAL, "=ownerId": deal_bitrix_id}
    )
    out: list[tuple[int, dict]] = []
    for row in rows:
        pid = getattr(row, "productId", None)
        if pid is None:
            continue
        order_id = await get_maas_id(db, int(pid), "product")
        if order_id is None:
            continue
        attrs = _row_to_order_attrs(row)
        out.append((order_id, attrs))
    return out


async def run_deal_sync(
    client: BitrixClient,
    redis: Redis,
    db: AsyncSession,
) -> None:
    """List modified deals, resolve to MaaS kits, skip create-only, fetch product rows, apply updates. Persist timestamp after run."""
    filter_ts = await get_sync_ts_for_filter(redis, "deal")
    bitrix_ids = await list_modified_deal_ids(client, filter_ts)
    filter_ts = _now_iso()
    deal_svc = DealService(client)
    for bitrix_id in bitrix_ids:
        maas_id = await get_maas_id(db, bitrix_id, "deal")
        if maas_id is None:
            continue
        try:
            deal = await deal_svc.get(bitrix_id)
            if _is_create_only_deal(deal):
                continue
            rows_with_attrs = await _deal_product_rows_with_order_attrs(
                client, db, bitrix_id
            )
            for order_id, attrs in rows_with_attrs:
                update_fields = {
                    k: v for k, v in attrs.items() if v is not None
                }
                if not update_fields:
                    continue
                try:
                    await orders_repo.update_order(
                        db, order_id, schemas.OrderUpdate(**update_fields)
                    )
                except Exception as exc:
                    logger.warning(
                        "Reverse sync deal product row → order order_id=%s failed: %s",
                        order_id,
                        exc,
                        exc_info=True,
                    )
            order_ids = [order_id for order_id, _ in rows_with_attrs]
            payload = await deal_to_kit_update(db, deal, order_ids)
            if not payload:
                continue
            kit = await kits_repo.get_kit_by_id(db, maas_id)
            await kits_repo.update_kit(
                db,
                kit,
                kit_name=payload.get("kit_name"),
                status=payload.get("status"),
                kit_price=payload.get("kit_price"),
                delivery_price=payload.get("delivery_price"),
                location=payload.get("location"),
                order_ids=payload.get("order_ids"),
            )
        except Exception as exc:
            logger.warning("Reverse sync deal bitrix_id=%s maas_id=%s failed: %s", bitrix_id, maas_id, exc, exc_info=True)
    await set_last_sync_ts(redis, "deal", filter_ts)


async def run_reverse_sync(
    client: BitrixClient,
    redis: Redis,
    db: AsyncSession,
) -> None:
    """Run only deal/product reverse sync. Users are one-way synced from MaaS to Bitrix."""
    await run_deal_sync(client, redis, db)
    await run_product_sync(client, redis, db)


async def run_loop(
    client: BitrixClient,
    redis: Redis,
    *,
    interval_seconds: int = 600,
) -> None:
    """Run reverse sync on a schedule (sleep between runs). Does not use the direct-sync Redis queue.
    Use as a dedicated process/entry point. Creates its own DB session per run.
    """
    import asyncio
    from backend.database import AsyncSessionLocal

    logger.info("Starting reverse sync loop (interval=%ss)", interval_seconds)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await run_reverse_sync(client, redis, db)
        except Exception as exc:
            logger.exception("Reverse sync run failed: %s", exc)
        await asyncio.sleep(interval_seconds)
