import json
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models, schemas
from backend.kits import repository as kits_repo

async def _parse_order_ids(value) -> List[int]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            v = json.loads(value)
            return [int(x) for x in v] if isinstance(v, list) else []
        except Exception:
            return []
    if isinstance(value, list):
        return [int(x) for x in value]
    return []

async def create_kit_from_orders(
    db: AsyncSession,
    *,
    current_user: models.User,
    kit_name: Optional[str],
    quantity: int,
    status: str = "pending",
    bitrix_deal_id: Optional[int] = None,
    location: Optional[str] = None,
    order_ids: List[int],
) -> models.Kit:
    order_ids = [int(x) for x in order_ids]
    if not order_ids:
        raise ValueError("order_ids must be a non-empty list")

    # Load orders and validate ownership
    res = await db.execute(select(models.Order).where(models.Order.order_id.in_(order_ids)))
    orders = res.scalars().all()
    found = {o.order_id for o in orders}
    missing = [oid for oid in order_ids if oid not in found]
    if missing:
        raise ValueError(f"Orders not found: {missing}")

    if not current_user.is_admin:
        foreign = [o.order_id for o in orders if o.user_id != current_user.id]
        if foreign:
            raise ValueError(f"Orders do not belong to current user: {foreign}")

    kit = await kits_repo.create_kit(
        db,
        user_id=current_user.id if not current_user.is_admin else orders[0].user_id,
        kit_name=kit_name,
        quantity=quantity,
        status=status,
        bitrix_deal_id=bitrix_deal_id,
        location=location,
        order_ids=order_ids,
    )

    for o in orders:
        o.kit_id = kit.kit_id
        db.add(o)
    await db.commit()

    # recalc prices
    kit = await kits_repo.recalc_kit_prices(db, kit.kit_id)

    return kit

async def add_order_to_kit(
    db: AsyncSession,
    *,
    kit_id: int,
    order_id: int,
    current_user: models.User
) -> models.Kit:
    kit = await kits_repo.get_kit_by_id(db, kit_id)
    if not kit:
        raise ValueError("Kit not found")

    order_res = await db.execute(select(models.Order).where(models.Order.order_id == order_id))
    order = order_res.scalar_one_or_none()
    if not order:
        raise ValueError("Order not found")

    # Permissions
    if not current_user.is_admin:
        if kit.user_id != current_user.id:
            raise ValueError("Access denied to kit")
        if order.user_id != current_user.id:
            raise ValueError("Access denied to order")

    order.kit_id = kit_id
    db.add(order)
    await db.commit()

    ids = await _parse_order_ids(kit.order_ids)
    if order_id not in ids:
        ids.append(order_id)
        kit = await kits_repo.update_kit_order_ids(db, kit, ids)
    
    kit = await kits_repo.recalc_kit_prices(db, kit_id)
    return kit

async def get_kit(
    db: AsyncSession,
    *,
    kit_id: int,
    current_user: models.User
) -> models.Kit:
    kit = await kits_repo.get_kit_by_id(db, kit_id)
    if not kit:
        raise ValueError("Kit not found")
    if not current_user.is_admin and kit.user_id != current_user.id:
        raise ValueError("Access denied")
    
    kit = await kits_repo.recalc_kit_prices(db, kit_id)

    return kit

async def list_my_kits(db: AsyncSession, *, current_user: models.User) -> List[models.Kit]:
    if current_user.is_admin:
        return await kits_repo.get_all_kits(db)
    return await kits_repo.list_kits_by_user(db, current_user.id)

async def list_all_kits(db: AsyncSession, *, current_user: models.User) -> List[models.Kit]:
    if not current_user.is_admin:
        raise ValueError("Access denied")
    return await kits_repo.get_all_kits(db)

async def remove_order_from_kits(
    db: AsyncSession,
    *,
    order_id: int,
    current_user: models.User,
    owner_user_id: int,
) -> int:
    """
    Remove order_id from kits of the order owner.
    owner_user_id — владелец заказа. Для не-админа = current_user.id
    """
    # Permissions: non-admin can only affect own kits
    if not current_user.is_admin and owner_user_id != current_user.id:
        raise ValueError("Access denied")

    return await kits_repo.remove_order_from_user_kits(db, user_id=owner_user_id, order_id=order_id)

async def update_kit(
    db: AsyncSession,
    *,
    kit_id: int,
    current_user: models.User,
    kit_name: Optional[str] = None,
    quantity: Optional[int] = None,
    status: Optional[str] = None,
    bitrix_deal_id: Optional[int] = None,
    location: Optional[str] = None,
    order_ids: Optional[List[int]] = None,
) -> models.Kit:
    kit = await kits_repo.get_kit_by_id(db, kit_id)
    if not kit:
        raise ValueError("Kit not found")

    # Permissions
    if not current_user.is_admin and kit.user_id != current_user.id:
        raise ValueError("Access denied")

    # Если обновляют order_ids — валидируем существование заказов и владение
    if order_ids is not None:
        order_ids = [int(x) for x in order_ids]
        if not order_ids:
            raise ValueError("order_ids must be a non-empty list")

        res = await db.execute(select(models.Order).where(models.Order.order_id.in_(order_ids)))
        orders = res.scalars().all()
        found = {o.order_id for o in orders}
        missing = [oid for oid in order_ids if oid not in found]
        if missing:
            raise ValueError(f"Orders not found: {missing}")

        if not current_user.is_admin:
            foreign = [o.order_id for o in orders if o.user_id != current_user.id]
            if foreign:
                raise ValueError(f"Orders do not belong to current user: {foreign}")

    kit = await kits_repo.update_kit(
        db,
        kit,
        kit_name=kit_name,
        quantity=quantity,
        status=status,
        bitrix_deal_id=bitrix_deal_id,
        location=location,
        order_ids=order_ids,
    )
    kit = await kits_repo.recalc_kit_prices(db, kit.kit_id)
    return kit


async def delete_kit(
    db: AsyncSession,
    *,
    kit_id: int,
    current_user: models.User,
) -> bool:
    """
    Soft delete (cancel) kit.
    Non-admin can delete only own kit.
    """
    kit = await kits_repo.get_kit_by_id(db, kit_id)
    if not kit:
        raise ValueError("Kit not found")

    if not current_user.is_admin and kit.user_id != current_user.id:
        raise ValueError("Access denied")

    ok = await kits_repo.soft_delete_kit(db, kit_id)
    return ok


async def hard_delete_kit(
    db: AsyncSession,
    *,
    kit_id: int,
    current_user: models.User,
) -> bool:
    """
    Hard delete kit (admin only).
    """
    if not current_user.is_admin:
        raise ValueError("Access denied")

    ok = await kits_repo.hard_delete_kit(db, kit_id)
    if not ok:
        raise ValueError("Kit not found")
    return ok
