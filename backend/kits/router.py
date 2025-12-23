from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from backend.core.dependencies import get_request_db as get_db
from backend.auth.dependencies import get_current_user, get_current_admin_user
from backend import models, schemas
from backend.kits.service import (
    create_kit_from_orders, get_kit, list_my_kits, update_kit,
    list_all_kits, delete_kit, hard_delete_kit
)

router = APIRouter()

@router.post("/kits", response_model=schemas.KitOut, tags=["Kits"])
async def create_kit_endpoint(
    payload: schemas.KitCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        kit = await create_kit_from_orders(
            db,
            current_user=current_user,
            kit_name=payload.kit_name,
            quantity=payload.quantity,
            status=payload.status or "NEW",
            bitrix_deal_id=payload.bitrix_deal_id,
            location=payload.location,
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

@router.put("/kits/{kit_id}", response_model=schemas.KitOut, tags=["Kits"])
async def update_kit_endpoint(
    kit_id: int,
    payload: schemas.KitUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        kit = await update_kit(
            db,
            kit_id=kit_id,
            current_user=current_user,
            kit_name=payload.kit_name,
            quantity=payload.quantity,
            status=payload.status,
            bitrix_deal_id=payload.bitrix_deal_id,
            location=payload.location,
            order_ids=payload.order_ids,
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
        return {"success": ok}
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 403 if "access" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg)
