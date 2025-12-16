"""Investigate missing deals - check when orders were created and if they should be re-queued"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.database import get_db
from backend import models
from sqlalchemy import select
from datetime import datetime

async def investigate():
    print("=" * 60)
    print("Investigating Missing Deals")
    print("=" * 60)
    
    missing_deal_ids = [20, 21, 22, 23, 24, 25, 26, 27, 28, 30, 31]
    
    async for db in get_db():
        # Get orders with missing deal IDs
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.in_(missing_deal_ids))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        print(f"\nFound {len(orders)} orders with missing deal IDs")
        print("\nOrder Details:")
        print("-" * 60)
        
        for order in orders:
            created_at = order.created_at.strftime("%Y-%m-%d %H:%M:%S") if order.created_at else "N/A"
            updated_at = order.updated_at.strftime("%Y-%m-%d %H:%M:%S") if order.updated_at else "N/A"
            
            print(f"\nOrder {order.order_id}:")
            print(f"  Bitrix Deal ID: {order.bitrix_deal_id}")
            print(f"  Service: {order.service_id}")
            print(f"  Status: {order.status}")
            print(f"  Created: {created_at}")
            print(f"  Updated: {updated_at}")
            print(f"  Has file_id: {order.file_id is not None}")
            print(f"  Total Price: {order.total_price}")
        
        # Check if there are any orders without bitrix_deal_id that should have one
        print(f"\n" + "=" * 60)
        print("Checking orders without bitrix_deal_id:")
        print("=" * 60)
        
        result2 = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.is_(None))
            .order_by(models.Order.order_id.desc())
            .limit(10)
        )
        orders_without_deal = result2.scalars().all()
        
        print(f"\nFound {len(orders_without_deal)} recent orders without bitrix_deal_id (showing up to 10):")
        for order in orders_without_deal:
            created_at = order.created_at.strftime("%Y-%m-%d %H:%M:%S") if order.created_at else "N/A"
            print(f"  Order {order.order_id}: Created {created_at}, Status: {order.status}")
        
        print("\n" + "=" * 60)
        print("Analysis:")
        print("=" * 60)
        print(f"Missing deals: {missing_deal_ids}")
        print(f"These deals were likely created in the OLD Bitrix instance.")
        print(f"Recommendation: Clear bitrix_deal_id for these orders and re-queue them.")
        print("=" * 60)
        
        break

if __name__ == "__main__":
    asyncio.run(investigate())






