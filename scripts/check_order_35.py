"""Check order 35"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 35)
        )
        order = result.scalar_one_or_none()
        
        if order:
            print(f"Order 35:")
            print(f"  Status: {order.status}")
            print(f"  Bitrix Deal ID: {order.bitrix_deal_id or 'Not created yet'}")
            print(f"  Total Price: {order.total_price}")
        else:
            print("Order 35 not found")

if __name__ == "__main__":
    asyncio.run(main())


