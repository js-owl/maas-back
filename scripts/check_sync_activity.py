"""Check sync activity and recent stage updates"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select

async def check():
    """Check recent sync activity"""
    async with AsyncSessionLocal() as db:
        # Get orders that were updated in the last 10 minutes
        ten_minutes_ago = datetime.now() - timedelta(minutes=10)
        
        result = await db.execute(
            select(models.Order)
            .where(
                models.Order.bitrix_deal_id.isnot(None),
                models.Order.updated_at >= ten_minutes_ago
            )
            .order_by(models.Order.updated_at.desc())
        )
        recent_orders = result.scalars().all()
        
        print("=" * 100)
        print("RECENT ORDER UPDATES (Last 10 minutes)")
        print("=" * 100)
        
        if recent_orders:
            print(f"\nFound {len(recent_orders)} order(s) updated recently:\n")
            print(f"{'Order ID':<10} {'Status':<15} {'Deal ID':<10} {'Updated At':<25}")
            print("-" * 100)
            for order in recent_orders:
                print(f"{order.order_id:<10} {order.status:<15} {order.bitrix_deal_id or 'N/A':<10} {order.updated_at}")
        else:
            print("\nNo orders updated in the last 10 minutes.")
            print("This could mean:")
            print("  1. No deal stages were changed in Bitrix")
            print("  2. The sync hasn't run yet (runs every 5 minutes)")
            print("  3. The sync ran but no changes were detected")
        
        # Check when sync last ran
        print("\n" + "=" * 100)
        print("SYNC SCHEDULER STATUS")
        print("=" * 100)
        print("The sync scheduler runs every 5 minutes.")
        print("Check the logs with: docker logs backend --tail 100 | grep DEAL_SYNC_SCHEDULER")

if __name__ == "__main__":
    asyncio.run(check())


