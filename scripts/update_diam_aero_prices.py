#!/usr/bin/env python3
"""
Update prices for diam-aero user orders manually
Based on screenshots in demo/ folder
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update

# Import backend modules
from backend.models import User, Order
from backend.utils.logging import get_logger

logger = get_logger(__name__)

# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///./data/shop.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Price mappings based on screenshots
# Updated with correct prices from user
ORDER_PRICE_MAPPINGS = {
    4: {  # Order 4: cnc-milling, alum_D16
        "total_price": 44652.43,
        "detail_price": 44652.43,
        "detail_price_one": 44652.43,
        "mat_price": 15000.0,  # Estimated material cost
        "work_price": 29652.43  # Estimated work cost
    },
    5: {  # Order 5: cnc-milling, alum_AMG5
        "total_price": 29341.98,
        "detail_price": 29341.98,
        "detail_price_one": 29341.98,
        "mat_price": 10000.0,  # Estimated material cost
        "work_price": 19341.98  # Estimated work cost
    },
    6: {  # Order 6: cnc-milling, alum_D16
        "total_price": 35343.3,
        "detail_price": 35343.3,
        "detail_price_one": 35343.3,
        "mat_price": 12000.0,  # Estimated material cost
        "work_price": 23343.3  # Estimated work cost
    }
}

async def update_order_prices():
    """Update prices for diam-aero orders"""
    logger.info("Starting manual price update for diam-aero orders...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Get user
            result = await db.execute(select(User).where(User.username == "diam-aero"))
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error("User diam-aero not found")
                return
            
            logger.info(f"Found user diam-aero (ID: {user.id})")
            
            # Get all orders for the user
            result = await db.execute(select(Order).where(Order.user_id == user.id))
            orders = result.scalars().all()
            
            logger.info(f"Found {len(orders)} orders to update")
            
            # Update each order with new prices
            for order in orders:
                if order.order_id in ORDER_PRICE_MAPPINGS:
                    price_data = ORDER_PRICE_MAPPINGS[order.order_id]
                    
                    logger.info(f"\nUpdating order {order.order_id}...")
                    logger.info(f"  Service: {order.service_id}")
                    logger.info(f"  Material: {order.material_id}")
                    logger.info(f"  Old total_price: {order.total_price}")
                    logger.info(f"  New total_price: {price_data['total_price']}")
                    
                    # Update the order with new prices
                    await db.execute(
                        update(Order)
                        .where(Order.order_id == order.order_id)
                        .values(**price_data)
                    )
                    
                    logger.info(f"  Order {order.order_id} updated successfully!")
                else:
                    logger.warning(f"  No price mapping found for order {order.order_id}")
            
            # Commit all changes
            await db.commit()
            logger.info("\nAll price updates committed to database")
            
            # Verification
            logger.info("\nVerifying updated prices...")
            result = await db.execute(select(Order).where(Order.user_id == user.id))
            updated_orders = result.scalars().all()
            
            for order in updated_orders:
                logger.info(f"  Order {order.order_id}: {order.service_id}, {order.material_id}, total_price={order.total_price}")
            
            logger.info("\nPrice update completed successfully!")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error updating prices: {e}")
            await db.rollback()
            raise

async def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("MANUAL PRICE UPDATE FOR DIAM-AERO ORDERS")
    logger.info("=" * 60)
    
    try:
        await update_order_prices()
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
