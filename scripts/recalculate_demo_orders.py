#!/usr/bin/env python3
"""
Recalculate prices for existing diam-aero orders
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from backend.models import User, FileStorage, Order
from backend.calculations.service import call_calculator_service
from backend.utils.logging import get_logger

logger = get_logger(__name__)

# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///./data/shop.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def recalculate_order_prices():
    """Recalculate prices for diam-aero orders"""
    logger.info("Starting order price recalculation...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Get user
            result = await db.execute(select(User).where(User.username == "diam-aero"))
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error("User diam-aero not found")
                return
            
            logger.info(f"Found user diam-aero (ID: {user.id})")
            
            # Get all orders
            result = await db.execute(select(Order).where(Order.user_id == user.id))
            orders = result.scalars().all()
            
            logger.info(f"Found {len(orders)} orders to recalculate")
            
            for order in orders:
                logger.info(f"\nRecalculating order {order.order_id}...")
                logger.info(f"  Current price: {order.total_price}")
                logger.info(f"  Material: {order.material_id}")
                
                # Get file
                result = await db.execute(select(FileStorage).where(FileStorage.id == order.file_id))
                file_record = result.scalar_one_or_none()
                
                if not file_record:
                    logger.error(f"  File {order.file_id} not found, skipping")
                    continue
                
                logger.info(f"  File: {file_record.original_filename}")
                
                # Get file data
                with open(file_record.file_path, 'rb') as f:
                    file_data = f.read()
                
                import base64
                base64_data = base64.b64encode(file_data).decode('utf-8')
                
                # Calculate price
                try:
                    result = await call_calculator_service(
                        service_id="cnc-milling",
                        material_id=order.material_id,
                        material_form="rod",
                        quantity=1,
                        length=None,
                        width=None,
                        height=None,
                        n_dimensions=1,
                        tolerance_id="1",
                        finish_id="1",
                        cover_id=["1"],
                        k_otk="1",
                        k_cert=["a", "f"],
                        file_data=base64_data,
                        file_name=file_record.original_filename,
                        file_type=file_record.file_type
                    )
                    
                    # Update order
                    order.total_price = result.get("total_price")
                    order.detail_price = result.get("detail_price")
                    order.detail_price_one = result.get("detail_price_one")
                    order.mat_volume = result.get("mat_volume")
                    order.mat_weight = result.get("mat_weight")
                    order.mat_price = result.get("mat_price")
                    order.work_price = result.get("work_price")
                    order.k_quantity = result.get("k_quantity")
                    order.detail_time = result.get("detail_time")
                    order.total_time = result.get("total_time")
                    order.manufacturing_cycle = result.get("manufacturing_cycle")
                    order.calculation_type = result.get("calculation_type")
                    order.ml_model = result.get("ml_model")
                    order.ml_confidence = result.get("ml_confidence")
                    order.calculation_time = result.get("calculation_time")
                    order.total_calculation_time = result.get("total_calculation_time")
                    
                    await db.commit()
                    
                    logger.info(f"  New price: {order.total_price}")
                    logger.info(f"  Calculation type: {order.calculation_type}")
                    
                except Exception as e:
                    logger.error(f"  Error calculating: {e}")
                    import traceback
                    logger.error(f"  Traceback: {traceback.format_exc()}")
            
            logger.info("\nRecalculation completed!")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(recalculate_order_prices())

