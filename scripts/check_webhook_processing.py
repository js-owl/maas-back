"""Check if webhook was processed and order was updated"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.database import get_db
from backend import models
from sqlalchemy import select

async def check():
    print("=" * 80)
    print("Checking Webhook Processing Results")
    print("=" * 80)
    
    async for db in get_db():
        # Check order 10 (which has deal 51)
        result = await db.execute(
            select(models.Order)
            .where(models.Order.order_id == 10)
        )
        order = result.scalar_one_or_none()
        
        if order:
            print(f"\nOrder {order.order_id}:")
            print(f"  Bitrix Deal ID: {order.bitrix_deal_id}")
            print(f"  Status: {order.status}")
            print(f"  Total Price: {order.total_price}")
            print(f"  Updated At: {order.updated_at}")
        else:
            print("\nOrder 10 not found")
        
        # Check all orders with deal 51
        result2 = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id == 51)
        )
        orders = result2.scalars().all()
        
        if orders:
            print(f"\nOrders with deal 51: {len(orders)}")
            for o in orders:
                print(f"  Order {o.order_id}: Status={o.status}, Price={o.total_price}")
        else:
            print("\nNo orders found with deal 51")
        
        break

if __name__ == "__main__":
    asyncio.run(check())






