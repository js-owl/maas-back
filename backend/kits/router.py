from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from backend.core.dependencies import get_request_db as get_db
from backend.core.redis import get_redis
from backend.core.config import BITRIX_ENABLED
from backend.auth.dependencies import get_current_user, get_current_admin_user
from backend import models, schemas
from backend.kits.service import (
    create_kit_from_orders, get_kit, list_my_kits, update_kit,
    list_all_kits, delete_kit, hard_delete_kit, get_kit_calculation_summary
)
from backend.bitrix24.async_queue import enqueue_operation
from backend.bitrix24.repositories.mapping_repository import get_bitrix_id
from backend.bitrix24.sync_payload.deal import kit_to_deal_create, kit_to_deal_update
from backend.bitrix24.sync_payload.product import order_to_product_create, order_to_product_update
from backend.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/kits", response_model=schemas.KitOut, tags=["Kits"])
async def create_kit_endpoint(
    payload: schemas.KitCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    try:
        kit = await create_kit_from_orders(
            db,
            current_user=current_user,
            kit_name=payload.kit_name,
            quantity=payload.quantity,
            status=payload.status or "AWAITING_CONFIRMATION",
            location=payload.location, # DEPRECATED
            order_ids=payload.order_ids,
        )
        return kit
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/kits", response_model=List[schemas.KitOut], tags=["Kits"])
async def list_kits_endpoint(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_my_kits(db, current_user=current_user)

@router.get("/kits/{kit_id}", response_model=schemas.KitOut, tags=["Kits"])
async def get_kit_endpoint(
    kit_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_kit(db, kit_id=kit_id, current_user=current_user)
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 403 if "access" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg)
    
@router.get("/kits/{kit_id}/calculation_summary", response_model=schemas.KitSummaryResponse, tags=["Kits"])
async def get_kit_calculation_summary_endpoint(
    kit_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_kit_calculation_summary(db, kit_id=kit_id, current_user=current_user)
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 403 if "access" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg)

@router.put("/kits/{kit_id}/confirm", response_model=schemas.KitOut, tags=["Kits"])
async def confirm_kit_endpoint(
    kit_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Sync a kit and all its orders to Bitrix24 (full initial push)."""
    try:
        kit = await get_kit(db, kit_id=kit_id, current_user=current_user)
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 403 if "access" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg)

    if kit.status != "AWAITING_CONFIRMATION":
        raise HTTPException(
            status_code=400,
            detail=f"Kit cannot be confirmed: expected status AWAITING_CONFIRMATION, got {kit.status!r}",
        )

    if not BITRIX_ENABLED:
        return kit

    if not kit.orders:
        raise HTTPException(status_code=400, detail="Kit has no orders to confirm")

    for order in kit.orders:
        try:
            bitrix_product_id = await get_bitrix_id(db, order.order_id, "product")
            if bitrix_product_id is None:
                product_dto = await order_to_product_create(db, order)
                await enqueue_operation(
                    entity_type="product",
                    action="create",
                    payload=product_dto.model_dump(exclude_none=True),
                    local_id=order.order_id,
                    redis=redis,
                )
            else:
                product_dto = await order_to_product_update(db, order)
                await enqueue_operation(
                    entity_type="product",
                    action="update",
                    payload=product_dto.model_dump(exclude_none=True),
                    local_id=order.order_id,
                    external_id=bitrix_product_id,
                    redis=redis,
                )
        except Exception:
            logger.exception(
                "Failed to enqueue Bitrix24 product sync for order %s during kit %s confirmation",
                order.order_id,
                kit_id,
            )

    try:
        bitrix_deal_id = await get_bitrix_id(db, kit_id, "deal")
        if bitrix_deal_id is None:
            deal_dto = await kit_to_deal_create(db, kit)
            await enqueue_operation(
                entity_type="deal",
                action="create",
                payload=deal_dto.model_dump(exclude_none=True),
                local_id=kit_id,
                redis=redis,
            )
        else:
            deal_dto = await kit_to_deal_update(db, kit)
            await enqueue_operation(
                entity_type="deal",
                action="update",
                payload=deal_dto.model_dump(exclude_none=True),
                local_id=kit_id,
                external_id=bitrix_deal_id,
                redis=redis,
            )
    except Exception:
        logger.exception(
            "Failed to enqueue Bitrix24 deal sync for kit %s during confirmation",
            kit_id,
        )

    kit = await update_kit(db, kit_id=kit_id, current_user=current_user, status="NEW")
    return kit


@router.put("/kits/{kit_id}", response_model=schemas.KitOut, tags=["Kits"])
async def update_kit_endpoint(
    kit_id: int,
    payload: schemas.KitUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    try:
        kit = await update_kit(
            db,
            kit_id=kit_id,
            current_user=current_user,
            kit_name=payload.kit_name,
            quantity=payload.quantity,
            status=payload.status,
            kit_price=payload.kit_price,
            delivery_price=payload.delivery_price,
            location=payload.location,
            order_ids=payload.order_ids,
        )
        if BITRIX_ENABLED:
            bitrix_deal_id = await get_bitrix_id(db, kit_id, "deal")
            if bitrix_deal_id is not None:
                try:
                    deal_dto = await kit_to_deal_update(db, kit)
                    deal_payload = deal_dto.model_dump(exclude_none=True)
                    await enqueue_operation(
                        entity_type="deal",
                        action="update",
                        payload=deal_payload,
                        local_id=kit_id,
                        external_id=bitrix_deal_id,
                        redis=redis,
                    )
                except Exception:
                    logger.exception(
                        "Failed to enqueue Bitrix24 deal update for kit %s",
                        kit_id,
                    )
        return kit
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 403 if "access" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg)

@router.get("/admin/kits", response_model=List[schemas.KitOut], tags=["Admin", "Kits"])
async def list_all_kits_endpoint(
    current_user: models.User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_all_kits(db, current_user=current_user)

@router.delete("/kits/{kit_id}", tags=["Kits"])
async def delete_kit_endpoint(
    kit_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        ok = await delete_kit(db, kit_id=kit_id, current_user=current_user)
        return {"success": ok}
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 403 if "access" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg)

@router.delete("/admin/kits/{kit_id}/hard", tags=["Admin", "Kits"])
async def hard_delete_kit_endpoint(
    kit_id: int,
    current_user: models.User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        ok = await hard_delete_kit(db, kit_id=kit_id, current_user=current_user)
        return {"success": ok, "message": "Kit permanently deleted"}
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 403 if "access" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg)
