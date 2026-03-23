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
    location: Optional[str] = None, # DEPRECATED
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

    res_loc = await db.execute(
        select(models.User.location)
        .where(models.User.id == current_user.id)
    )
    user_location = res_loc.scalar_one_or_none()

    kit = await kits_repo.create_kit(
        db,
        user_id=current_user.id if not current_user.is_admin else orders[0].user_id,
        kit_name=kit_name,
        quantity=quantity,
        status=status,
        location=user_location,
        order_ids=order_ids,
    )
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
    kit_price: Optional[float] = None,
    delivery_price: Optional[float] = None,
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
        kit_price=kit_price,
        delivery_price=delivery_price,
        location=location,
        order_ids=order_ids,
    )
    kit = await kits_repo.recalc_kit_prices(db, kit.kit_id)
    return kit


async def get_kit_calculation_summary(
    db: AsyncSession,
    kit_id: int,
    current_user: models.User
) -> schemas.KitSummaryResponse:
    
    # check user, update kit
    kit = await get_kit(db, kit_id=kit_id, current_user=current_user)

    # parse order_ids
    if kit.order_ids is None:
        order_ids: List[int] = []
    elif isinstance(kit.order_ids, str):
        try:
            parsed = json.loads(kit.order_ids)
            order_ids = [int(x) for x in parsed] if isinstance(parsed, list) else []
        except Exception:
            order_ids = []
    else:
        order_ids = [int(x) for x in kit.order_ids]

    if not order_ids:
        kit_price = float(kit.kit_price or 0.0)
        return schemas.KitSummaryResponse(
            kit_id=kit.kit_id,
            kit_name=kit.kit_name,
            kit_quantity=kit.quantity,
            orders=[],
            kit_price=kit_price,
            total_kit_price=kit_price * (kit.quantity or 0),
        )

    # load orders
    res = await db.execute(
        select(models.Order).where(models.Order.order_id.in_(order_ids))
    )
    orders = res.scalars().all()

    # build summary
    items: List[schemas.OrderSummaryItem] = []
    total_kit_price_with_taxes = 0.0

    # order by kit.order_ids
    by_id = {o.order_id: o for o in orders}

    for oid in order_ids:
        o = by_id.get(oid)
        if not o:
            continue
        if (o.status or "").lower() in kits_repo.EXCLUDED_ORDER_STATUSES:
            continue

        unit_price = float(o.detail_price_one or 0.0)
        total_price = float(o.total_price or 0.0)

        item_summary = schemas.OrderSummaryItem(
            order_id=o.order_id,
            order_name=o.order_name,
            order_code=o.order_code,
            quantity=o.quantity or 0,
            unit_price=unit_price,
            total_price=total_price,
        )

        items.append(item_summary)
        total_price_with_taxes = item_summary.total_kit_price_with_taxes
        total_kit_price_with_taxes += total_price_with_taxes

    return schemas.KitSummaryResponse(
        kit_id=kit.kit_id,
        kit_name=kit.kit_name,
        kit_quantity=kit.quantity,
        orders=items,
        total_kit_price_with_taxes=total_kit_price_with_taxes
    )

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
