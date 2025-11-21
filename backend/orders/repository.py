"""
Orders repository module
Database operations for order management
"""
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend import models, schemas
from backend.utils.logging import get_logger

logger = get_logger(__name__)


async def create_order(db: AsyncSession, user_id: int, order: schemas.OrderCreate, file_id: int, calc: Dict | None = None) -> models.Order:
    """Create a new order"""
    # Note: service_id is now a calculator service ID string (e.g., "cnc_lathe")
    # No longer validates against local manufacturing services table
    
    # COMMENTED OUT: dimensions logic no longer needed when length/width/height provided
    # if not (order.length and order.width and order.height):
    #     raise ValueError("Dimensions are required for order creation")
    
    # Create order with calculator service integration
    db_order = models.Order(
        user_id=user_id,
        file_id=file_id,
        service_id=order.service_id,  # Store calculator service ID directly
        quantity=order.quantity,
        length=order.length,
        width=order.width,
        height=order.height,
        thickness=order.thickness,
        dia=order.dia,
        material_id=order.material_id,
        material_form=order.material_form,
        special_instructions=order.special_instructions,
        tolerance_id=order.tolerance_id,
        finish_id=order.finish_id,
        cover_id=order.cover_id,
        k_otk=order.k_otk,
        k_cert=order.k_cert,
        n_dimensions=order.n_dimensions,
        status='pending',
        # Store calculation results if provided
        mat_volume=calc.get('mat_volume') if calc else None,
        detail_price=calc.get('detail_price') if calc else None,
        detail_price_one=calc.get('detail_price_one') if calc else None,
        mat_weight=calc.get('mat_weight') if calc else None,
        mat_price=calc.get('mat_price') if calc else None,
        work_price=calc.get('work_price') if calc else None,
        k_quantity=calc.get('k_quantity') if calc else None,
        detail_time=calc.get('detail_time') if calc else None,
        total_price=calc.get('total_price') if calc else None,
        total_time=calc.get('total_time') if calc else None,
        manufacturing_cycle=calc.get('manufacturing_cycle') if calc else None,
        suitable_machines=json.dumps(calc.get('suitable_machines')) if calc and calc.get('suitable_machines') else None,
        total_price_breakdown=json.dumps(calc.get('total_price_breakdown')) if calc and calc.get('total_price_breakdown') else None,
        # Calculation type information
        calculation_type=calc.get('calculation_type') if calc else None,
        ml_model=calc.get('ml_model') if calc else None,
        ml_confidence=calc.get('ml_confidence') if calc else None,
        calculation_time=calc.get('calculation_time') if calc else None,
        total_calculation_time=calc.get('total_calculation_time') if calc else None
    )
    
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    return db_order


async def update_order_calc_fields(db: AsyncSession, order_id: int, calc: dict) -> Optional[models.Order]:
    """Persist calculator outputs and set total_price from calculator for an existing order."""
    order = await get_order_by_id(db, order_id)
    if not order:
        return None
    # Update fields
    order.mat_volume = calc.get('mat_volume')
    order.detail_price = calc.get('detail_price')
    order.detail_price_one = calc.get('detail_price_one')
    order.mat_weight = calc.get('mat_weight')
    order.mat_price = calc.get('mat_price')
    order.work_price = calc.get('work_price')
    order.k_quantity = calc.get('k_quantity')
    order.detail_time = calc.get('detail_time')
    order.total_price = calc.get('total_price')
    order.total_time = calc.get('total_time')
    order.manufacturing_cycle = calc.get('manufacturing_cycle')
    order.suitable_machines = json.dumps(calc.get('suitable_machines')) if calc.get('suitable_machines') else None
    # Update calculation type information
    order.calculation_type = calc.get('calculation_type')
    order.ml_model = calc.get('ml_model')
    order.ml_confidence = calc.get('ml_confidence')
    order.calculation_time = calc.get('calculation_time')
    order.total_calculation_time = calc.get('total_calculation_time')
    
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def get_order_by_id(db: AsyncSession, order_id: int) -> Optional[models.Order]:
    """Get order by ID with relationships"""
    try:
        result = await db.execute(
            select(models.Order)
            .options(selectinload(models.Order.file))  # Removed service relationship
            .where(models.Order.order_id == order_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        # If file relationship fails (e.g., file was deleted), try without the relationship
        logger.warning(f"Failed to load order with file relationship for order {order_id}: {e}")
        result = await db.execute(
            select(models.Order)
            .where(models.Order.order_id == order_id)
        )
        return result.scalar_one_or_none()


async def get_orders_by_user(db: AsyncSession, user_id: int) -> List[models.Order]:
    """Get all orders for a user without relationships (for OrderOutSimple)"""
    result = await db.execute(
        select(models.Order)
        .where(models.Order.user_id == user_id)
    )
    return result.scalars().all()


async def get_all_orders(db: AsyncSession) -> List[models.Order]:
    """Get all orders (admin only) with relationships"""
    result = await db.execute(
        select(models.Order)
        .where(models.Order.file_id.isnot(None))  # Filter out orders with NULL file_id
        .options(selectinload(models.Order.file), selectinload(models.Order.user))  # Removed service relationship
    )
    return result.scalars().all()


async def update_order(db: AsyncSession, order_id: int, order_update: schemas.OrderUpdate) -> Optional[models.Order]:
    """Update order and recalculate price if needed"""
    import json
    
    order = await get_order_by_id(db, order_id)
    if not order:
        return None
    
    # Update fields
    update_data = order_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        # Serialize document_ids to JSON string since it's stored as Text, not JSON
        if field == 'document_ids' and value is not None:
            if isinstance(value, list):
                setattr(order, field, json.dumps(value))
            else:
                setattr(order, field, value)
        # cover_id and k_cert are JSON columns - SQLAlchemy handles Python lists automatically
        # But ensure they're proper Python objects (lists) for JSON columns
        elif field in ('cover_id', 'k_cert') and value is not None:
            # JSON columns automatically serialize Python lists/dicts
            # Ensure value is a list if it's not None
            if isinstance(value, str):
                try:
                    # Try to parse as JSON if it's a string
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # If not valid JSON, convert to list
                    value = [str(value)]
            elif not isinstance(value, (list, dict)):
                # Convert non-list/dict to list for JSON column
                value = [str(value)] if value is not None else None
            setattr(order, field, value)
        else:
            setattr(order, field, value)
    
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def delete_order(db: AsyncSession, order_id: int) -> bool:
    """Cancel order by setting status to 'cancelled' instead of deleting."""
    order = await get_order_by_id(db, order_id)
    if not order:
        return False
    order.status = 'cancelled'
    db.add(order)
    await db.commit()
    return True


async def hard_delete_order(db: AsyncSession, order_id: int) -> bool:
    """Permanently delete an order (admin-only usage)."""
    order = await get_order_by_id(db, order_id)
    if not order:
        return False
    await db.delete(order)
    await db.commit()
    return True
