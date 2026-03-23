from typing import Any, Dict

from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.basket import repository as basket_repo
from backend.bitrix24.async_queue import enqueue_operation
from backend.bitrix24.sync_payload.deal import kit_to_deal_create
from backend.bitrix24.sync_payload.product import order_to_product_create
from backend.core.config import BITRIX_ENABLED
from backend.kits.service import create_kit_from_orders
from backend.orders.service import (
    create_order_with_calculation,
    create_order_with_dimensions,
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)


def _build_basket_out(items: Dict[str, Dict[str, Any]]) -> schemas.BasketOut:
    basket_items = [
        schemas.BasketItemOut(item_id=item_id, **payload)
        for item_id, payload in items.items()
    ]
    return schemas.BasketOut(items=basket_items)


async def add_to_basket(
    redis: Redis,
    user_id: int,
    item: schemas.BasketItemIn,
) -> schemas.BasketOut:
    await basket_repo.add_item(redis, user_id, item.model_dump())
    return await get_basket(redis, user_id)


async def get_basket(redis: Redis, user_id: int) -> schemas.BasketOut:
    items = await basket_repo.get_all_items(redis, user_id)
    return _build_basket_out(items)


async def update_basket_item(
    redis: Redis,
    user_id: int,
    item_id: str,
    patch: schemas.BasketItemUpdate,
) -> schemas.BasketOut:
    try:
        await basket_repo.update_item(redis, user_id, item_id, patch.model_dump(exclude_none=True))
    except KeyError:
        raise HTTPException(status_code=404, detail="Basket item not found")
    return await get_basket(redis, user_id)


async def remove_from_basket(redis: Redis, user_id: int, item_id: str) -> schemas.BasketOut:
    try:
        await basket_repo.delete_item(redis, user_id, item_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Basket item not found")
    return await get_basket(redis, user_id)


async def checkout_basket(
    db: AsyncSession,
    redis: Redis,
    current_user: models.User,
    payload: schemas.BasketCheckoutIn,
) -> models.Kit:
    items = await basket_repo.get_all_items(redis, current_user.id)
    if not items:
        raise HTTPException(status_code=400, detail="Basket is empty")

    created_orders = []
    for item_payload in items.values():
        order_payload = dict(item_payload)
        file_id = order_payload.pop("file_id", None)
        order_data = schemas.OrderCreate(**order_payload)

        if file_id is not None:
            db_order = await create_order_with_calculation(db, current_user.id, order_data, int(file_id))
        else:
            db_order = await create_order_with_dimensions(db, current_user.id, order_data)
        created_orders.append(db_order)

        if BITRIX_ENABLED:
            try:
                product_dto = await order_to_product_create(db, db_order)
                await enqueue_operation(
                    entity_type="product",
                    action="create",
                    payload=product_dto.model_dump(exclude_none=True),
                    local_id=db_order.order_id,
                    redis=redis,
                )
            except Exception:
                logger.exception(
                    "Failed to enqueue Bitrix24 product sync for order %s (basket checkout)",
                    db_order.order_id,
                )

    try:
        kit = await create_kit_from_orders(
            db,
            current_user=current_user,
            kit_name=payload.kit_name,
            quantity=payload.quantity,
            status=payload.status or "AWAITING_CONFIRMATION",
            location=payload.location or current_user.location,
            order_ids=[order.order_id for order in created_orders],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if BITRIX_ENABLED:
        try:
            deal_dto = await kit_to_deal_create(db, kit)
            await enqueue_operation(
                entity_type="deal",
                action="create",
                payload=deal_dto.model_dump(exclude_none=True),
                local_id=kit.kit_id,
                redis=redis,
            )
        except Exception:
            logger.exception(
                "Failed to enqueue Bitrix24 deal sync for kit %s (basket checkout)",
                kit.kit_id,
            )

    await basket_repo.clear_basket(redis, current_user.id)
    return kit


async def clear_basket(redis: Redis, user_id: int) -> None:
    await basket_repo.clear_basket(redis, user_id)
