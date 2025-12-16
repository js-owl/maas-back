"""Check if order 38 needs an update"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.sync_service import bitrix_sync_service
from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        # Get order 38
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 38)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("Order 38 not found!")
            return
        
        print(f"Order 38:")
        print(f"  Status: {order.status}")
        print(f"  Total Price: {order.total_price}")
        print(f"  Bitrix Deal ID: {order.bitrix_deal_id}")
        print(f"  Updated: {order.updated_at}")
        
        if order.bitrix_deal_id:
            # Check deal in Bitrix
            deal = await bitrix_client.get_deal(order.bitrix_deal_id)
            if deal:
                print(f"\nBitrix Deal {order.bitrix_deal_id}:")
                print(f"  Title: {deal.get('TITLE', 'N/A')}")
                print(f"  Opportunity (Price): {deal.get('OPPORTUNITY', 'N/A')}")
                print(f"  Stage: {deal.get('STAGE_ID', 'N/A')}")
                print(f"  Modified: {deal.get('DATE_MODIFY', 'N/A')}")
                
                # Check if update is needed
                deal_price = float(deal.get('OPPORTUNITY', 0) or 0)
                order_price = float(order.total_price or 0)
                
                if abs(deal_price - order_price) > 0.01:
                    print(f"\n⚠️  Price mismatch detected!")
                    print(f"   Order price: {order_price}")
                    print(f"   Deal price: {deal_price}")
                    print(f"   Queueing deal update...")
                    await bitrix_sync_service.queue_deal_update(db, order.order_id)
                    print(f"   ✓ Deal update queued")
                else:
                    print(f"\n✓ Deal is up to date")
            else:
                print(f"\n❌ Deal {order.bitrix_deal_id} not found in Bitrix")
        else:
            print(f"\n⚠️  No Bitrix deal ID - queueing creation...")
            await bitrix_sync_service.queue_deal_creation(
                db, 
                order.order_id, 
                order.user_id,
                order.file_id,
                order.document_ids
            )
            print(f"   ✓ Deal creation queued")

if __name__ == "__main__":
    asyncio.run(main())









