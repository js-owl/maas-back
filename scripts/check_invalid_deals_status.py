"""Check current status of orders with invalid deals"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select

async def check():
    """Check invalid deals"""
    invalid_deal_ids = [32, 33, 34, 35, 36, 37, 38]
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.in_(invalid_deal_ids))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        print("=" * 80)
        print("ORDERS WITH INVALID BITRIX DEALS")
        print("=" * 80)
        print(f"\n{'Order ID':<10} {'Current Status':<20} {'Deal ID':<10}")
        print("-" * 80)
        
        for order in orders:
            print(f"{order.order_id:<10} {order.status:<20} {order.bitrix_deal_id:<10}")
        
        print("\n" + "=" * 80)
        print("RECOMMENDATION:")
        print("=" * 80)
        print("These deals don't exist in Bitrix (return 400 Bad Request).")
        print("Since the deals were deleted, they should likely be set to 'LOSE' status.")
        print("However, order 23 already has 'cancelled' status - should it be 'LOSE'?")

if __name__ == "__main__":
    asyncio.run(check())


