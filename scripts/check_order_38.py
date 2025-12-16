"""Check order 38 and recent orders Bitrix status"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        # Check order 38
        result = await db.execute(
            select(models.Order)
            .where(models.Order.order_id == 38)
        )
        order_38 = result.scalar_one_or_none()
        
        if order_38:
            print("="*60)
            print(f"Order 38 Details:")
            print("="*60)
            print(f"Order ID: {order_38.order_id}")
            print(f"User ID: {order_38.user_id}")
            print(f"Service ID: {order_38.service_id}")
            print(f"Status: {order_38.status}")
            print(f"Bitrix Deal ID: {order_38.bitrix_deal_id}")
            print(f"Created At: {order_38.created_at}")
            print(f"Updated At: {order_38.updated_at}")
        else:
            print("Order 38 not found!")
        
        # Check recent orders without Bitrix deals
        print("\n" + "="*60)
        print("Recent orders without Bitrix deals:")
        print("="*60)
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.is_(None))
            .order_by(models.Order.order_id.desc())
            .limit(10)
        )
        orders = result.scalars().all()
        
        print(f"{'Order ID':<10} {'User ID':<10} {'Service ID':<15} {'Status':<15} {'Created At':<20}")
        print("-" * 80)
        for order in orders:
            print(f"{order.order_id:<10} {order.user_id:<10} {order.service_id:<15} {order.status:<15} {str(order.created_at)[:19] if order.created_at else 'N/A':<20}")

if __name__ == "__main__":
    asyncio.run(main())









