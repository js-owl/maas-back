"""Update all orders to attach files to their Bitrix deals"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.sync_service import bitrix_sync_service
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        # Get all orders with Bitrix deals
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        print(f"Found {len(orders)} orders with Bitrix deals")
        print("Queueing file attachment updates...")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for order in orders:
            try:
                # Queue deal update (which will attach files if available)
                await bitrix_sync_service.queue_deal_update(db, order.order_id)
                updated_count += 1
                if updated_count % 10 == 0:
                    print(f"  Queued {updated_count} orders...")
            except Exception as e:
                print(f"  Error queuing order {order.order_id}: {e}")
                error_count += 1
        
        print(f"\nCompleted:")
        print(f"  Total orders: {len(orders)}")
        print(f"  Queued for update: {updated_count}")
        print(f"  Errors: {error_count}")
        print(f"\nUpdates are queued to Redis and will be processed by the Bitrix worker.")

if __name__ == "__main__":
    asyncio.run(main())









