"""Check recent orders with Bitrix deals"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        # Get recent orders with Bitrix deals
        result = await db.execute(
            select(models.Order.order_id, models.Order.bitrix_deal_id, models.Order.status)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id.desc())
            .limit(10)
        )
        orders = result.all()
        
        print("Recent orders with Bitrix deals:")
        print(f"{'Order ID':<10} {'Deal ID':<10} {'Status':<15}")
        print("-" * 40)
        for o in orders:
            print(f"{o.order_id:<10} {o.bitrix_deal_id:<10} {o.status:<15}")

if __name__ == "__main__":
    asyncio.run(main())


