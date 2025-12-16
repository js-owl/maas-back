"""Find which deal IDs are causing 400 errors"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from sqlalchemy import select

async def find_400_errors():
    """Find which deals cause 400 errors"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        print("=" * 60)
        print("FINDING 400 ERROR DEALS")
        print("=" * 60)
        print(f"\nChecking {len(orders)} orders...\n")
        
        problematic = []
        
        for order in orders:
            deal_id = order.bitrix_deal_id
            try:
                deal_data = await bitrix_client.get_deal(deal_id)
                if not deal_data:
                    problematic.append((order.order_id, deal_id, "Not found (None returned)"))
            except Exception as e:
                error_str = str(e)
                if "400" in error_str or "Bad Request" in error_str:
                    problematic.append((order.order_id, deal_id, error_str[:50]))
        
        if problematic:
            print(f"Found {len(problematic)} problematic deals:\n")
            print(f"{'Order ID':<10} {'Deal ID':<10} {'Error':<50}")
            print(f"{'-'*10} {'-'*10} {'-'*50}")
            for order_id, deal_id, error in problematic:
                print(f"{order_id:<10} {deal_id:<10} {error:<50}")
        else:
            print("No 400 errors found in current orders")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(find_400_errors())

