"""Verify that missing deals have been recreated in Bitrix"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.database import get_db
from backend import models
from sqlalchemy import select
from backend.bitrix.client import bitrix_client

async def verify():
    print("=" * 60)
    print("Verifying Missing Deals Have Been Recreated")
    print("=" * 60)
    
    # Orders that had missing deals
    order_ids = [10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21]
    
    async for db in get_db():
        result = await db.execute(
            select(models.Order)
            .where(models.Order.order_id.in_(order_ids))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        print(f"\nChecking {len(orders)} orders:\n")
        
        recreated = 0
        still_missing = 0
        no_deal_id = 0
        
        for order in orders:
            if order.bitrix_deal_id:
                # Check if deal exists in Bitrix
                try:
                    deal = await bitrix_client.get_deal(order.bitrix_deal_id)
                    if deal:
                        deal_title = deal.get("TITLE", "N/A")
                        print(f"  ✅ Order {order.order_id}: Deal {order.bitrix_deal_id} exists - {deal_title}")
                        recreated += 1
                    else:
                        print(f"  ❌ Order {order.order_id}: Deal {order.bitrix_deal_id} still not found")
                        still_missing += 1
                except Exception as e:
                    if "Not found" in str(e) or "400" in str(e):
                        print(f"  ❌ Order {order.order_id}: Deal {order.bitrix_deal_id} still not found")
                        still_missing += 1
                    else:
                        print(f"  ⚠️  Order {order.order_id}: Error checking deal {order.bitrix_deal_id} - {e}")
            else:
                print(f"  ⏳ Order {order.order_id}: No deal_id yet (still processing)")
                no_deal_id += 1
        
        print(f"\n" + "=" * 60)
        print(f"Summary:")
        print(f"  ✅ Recreated and verified: {recreated}")
        print(f"  ❌ Still missing: {still_missing}")
        print(f"  ⏳ Still processing: {no_deal_id}")
        print("=" * 60)
        
        if no_deal_id > 0:
            print("\nNote: Some orders are still being processed by the worker.")
            print("      Wait a few moments and run this script again to verify.")
        
        break

if __name__ == "__main__":
    asyncio.run(verify())






