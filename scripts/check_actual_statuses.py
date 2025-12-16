"""Check actual order statuses in database"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select
from collections import Counter

async def check():
    """Check actual statuses"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        print("=" * 80)
        print("ACTUAL ORDER STATUSES IN DATABASE")
        print("=" * 80)
        print(f"\n{'Order ID':<10} {'Status':<25}")
        print("-" * 80)
        
        status_counts = Counter()
        for order in orders:
            print(f"{order.order_id:<10} {order.status:<25}")
            status_counts[order.status] += 1
        
        print("\n" + "=" * 80)
        print("STATUS DISTRIBUTION")
        print("=" * 80)
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")

if __name__ == "__main__":
    asyncio.run(check())


