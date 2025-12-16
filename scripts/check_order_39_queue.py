"""Check if order 39 deal creation is queued"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.sync_service import bitrix_sync_service
from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        # Get order 39
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 39)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("Order 39 not found!")
            return
        
        print(f"Order 39:")
        print(f"  Status: {order.status}")
        print(f"  User ID: {order.user_id}")
        print(f"  Bitrix Deal ID: {order.bitrix_deal_id or 'NOT SET'}")
        print(f"  Created: {order.created_at}")
        print(f"  Updated: {order.updated_at}")
        
        # Check if deal creation should be queued
        if not order.bitrix_deal_id:
            print(f"\n⚠️  Order 39 doesn't have a Bitrix deal ID")
            print(f"   Queueing deal creation now...")
            
            # Queue deal creation
            await bitrix_sync_service.queue_deal_creation(
                db, 
                order.order_id, 
                order.user_id,
                order.file_id,
                order.document_ids
            )
            
            print(f"   ✓ Deal creation queued to Redis")
            print(f"   The worker should process it shortly")
        else:
            print(f"\n✓ Order 39 already has Bitrix deal {order.bitrix_deal_id}")

if __name__ == "__main__":
    asyncio.run(main())









