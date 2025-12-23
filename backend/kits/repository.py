import json
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend import models


EXCLUDED_ORDER_STATUSES = {"cancelled"}


async def create_kit(
    db: AsyncSession,
    *,
    user_id: int,
    kit_name: Optional[str],
    quantity: int,
    status: str,
    bitrix_deal_id: Optional[int],
    location: Optional[str],
    order_ids: List[int],
) -> models.Kit:
    kit = models.Kit(
        user_id=user_id,
        kit_name=kit_name,
        quantity=quantity,
        status=status,
        bitrix_deal_id=bitrix_deal_id,
        location=location,
        order_ids=json.dumps([int(x) for x in order_ids]),
    )
    db.add(kit)
    await db.commit()
    await db.refresh(kit)
    return kit

async def get_all_kits(db) -> List[models.Kit]:
    """Get all kits (admin only)."""
    res = await db.execute(select(models.Kit))
    return res.scalars().all()

async def update_kit(
    db,
    kit: models.Kit,
    *,
    kit_name: Optional[str] = None,
    quantity: Optional[int] = None,
    status: Optional[str] = None,
    bitrix_deal_id: Optional[int] = None,
    location: Optional[str] = None,
    order_ids: Optional[list[int]] = None,
) -> models.Kit:
    if kit_name is not None:
        kit.kit_name = kit_name
    if quantity is not None:
        kit.quantity = quantity
    if status is not None:
        kit.status = status
    if bitrix_deal_id is not None:
        kit.bitrix_deal_id = bitrix_deal_id
    if location is not None:
        kit.location = location
    if order_ids is not None:
        kit.order_ids = json.dumps([int(x) for x in order_ids])

    db.add(kit)
    await db.commit()
    await db.refresh(kit)
    return kit

async def get_kit_by_id(db: AsyncSession, kit_id: int) -> Optional[models.Kit]:
    res = await db.execute(
        select(models.Kit)
        .where(models.Kit.kit_id == kit_id)
    )
    return res.scalar_one_or_none()

async def list_kits_by_user(db: AsyncSession, user_id: int) -> List[models.Kit]:
    res = await db.execute(
        select(models.Kit)
        .where(models.Kit.user_id == user_id)
    )
    return res.scalars().all()

async def update_kit_order_ids(db: AsyncSession, kit: models.Kit, order_ids: List[int]) -> models.Kit:
    kit.order_ids = json.dumps([int(x) for x in order_ids])
    db.add(kit)
    await db.commit()
    await db.refresh(kit)
    return kit

def _safe_parse_order_ids(value) -> List[int]:
    if value is None:
        return []
    if isinstance(value, list):
        return [int(x) for x in value]
    if isinstance(value, str):
        try:
            v = json.loads(value)
            if isinstance(v, list):
                return [int(x) for x in v]
            return []
        except Exception:
            return []
    return []


async def remove_order_from_user_kits(db: AsyncSession, *, user_id: int, order_id: int) -> int:
    res = await db.execute(select(models.Kit).where(models.Kit.user_id == user_id))
    kits = res.scalars().all()

    updated = 0
    for kit in kits:
        ids = _safe_parse_order_ids(kit.order_ids)
        if order_id in ids:
            ids = [x for x in ids if x != order_id]
            kit.order_ids = json.dumps(ids)
            db.add(kit)
            updated += 1

    if updated:
        await db.commit()
    return updated


async def recalc_kit_prices(db, kit_id: int) -> models.Kit:
    kit = await db.get(models.Kit, kit_id)
    if not kit:
        raise ValueError("Kit not found")

    res = await db.execute(
        select(func.coalesce(func.sum(models.Order.total_price), 0.0))
        .where(models.Order.kit_id == kit_id)
        .where(models.Order.status.notin_(EXCLUDED_ORDER_STATUSES))
    )
    kit_price = float(res.scalar() or 0.0)

    kit.kit_price = kit_price
    qty = int(kit.quantity or 1)
    kit.total_kit_price = float(kit_price * max(qty, 1))

    db.add(kit)
    await db.commit()
    await db.refresh(kit)
    return kit


async def soft_delete_kit(db: AsyncSession, kit_id: int) -> bool:
    """Soft delete kit by setting status to 'cancelled'."""
    kit = await db.get(models.Kit, kit_id)
    if not kit:
        return False

    kit.status = "cancelled"
    db.add(kit)
    await db.commit()
    await db.refresh(kit)
    return True


async def hard_delete_kit(db: AsyncSession, kit_id: int) -> bool:
    """
    Hard delete kit:
    - unlink orders: set Order.kit_id = NULL for orders in this kit (source of truth = orders.kit_id)
    - delete kit row
    """
    kit = await db.get(models.Kit, kit_id)
    if not kit:
        return False

    # Unlink orders from kit
    res = await db.execute(select(models.Order).where(models.Order.kit_id == kit_id))
    orders = res.scalars().all()
    for o in orders:
        o.kit_id = None
        db.add(o)

    await db.commit()

    await db.delete(kit)
    await db.commit()
    return True
