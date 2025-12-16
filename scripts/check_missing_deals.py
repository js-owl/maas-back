"""Check which deals from database are missing in Bitrix"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.database import get_db
from backend import models
from sqlalchemy import select
from backend.bitrix.client import bitrix_client

async def check_missing_deals():
    print("=" * 60)
    print("Checking Missing Deals in Bitrix")
    print("=" * 60)
    
    async for db in get_db():
        # Get all orders with deal IDs
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        print(f"\nFound {len(orders)} orders with bitrix_deal_id in database")
        print("\nChecking each deal in Bitrix...\n")
        
        missing_deals = []
        found_deals = []
        error_deals = []
        
        for order in orders:
            try:
                deal = await bitrix_client.get_deal(order.bitrix_deal_id)
                if deal:
                    deal_title = deal.get("TITLE", "N/A")
                    deal_stage = deal.get("STAGE_ID", "N/A")
                    deal_category = deal.get("CATEGORY_ID", "N/A")
                    print(f"  ✅ Order {order.order_id}: Deal {order.bitrix_deal_id} exists")
                    print(f"      Title: {deal_title}")
                    print(f"      Stage: {deal_stage}, Category: {deal_category}")
                    found_deals.append((order.order_id, order.bitrix_deal_id))
                else:
                    print(f"  ❌ Order {order.order_id}: Deal {order.bitrix_deal_id} NOT FOUND in Bitrix")
                    missing_deals.append((order.order_id, order.bitrix_deal_id))
            except Exception as e:
                error_msg = str(e)
                if "Not found" in error_msg or "400" in error_msg:
                    print(f"  ❌ Order {order.order_id}: Deal {order.bitrix_deal_id} NOT FOUND (error: {error_msg})")
                    missing_deals.append((order.order_id, order.bitrix_deal_id))
                else:
                    print(f"  ⚠️  Order {order.order_id}: Deal {order.bitrix_deal_id} - Error checking: {e}")
                    error_deals.append((order.order_id, order.bitrix_deal_id, error_msg))
        
        print(f"\n" + "=" * 60)
        print(f"Summary:")
        print(f"  Found in Bitrix: {len(found_deals)}")
        print(f"  Missing from Bitrix: {len(missing_deals)}")
        print(f"  Errors checking: {len(error_deals)}")
        
        if missing_deals:
            print(f"\nMissing Deals:")
            for order_id, deal_id in missing_deals:
                print(f"  Order {order_id} -> Deal {deal_id}")
        
        if error_deals:
            print(f"\nErrors:")
            for order_id, deal_id, error in error_deals:
                print(f"  Order {order_id} -> Deal {deal_id}: {error}")
        
        # Check if we can find these deals by searching
        if missing_deals:
            print(f"\n" + "=" * 60)
            print("Checking if deals exist with different IDs (searching by order number)...")
            for order_id, deal_id in missing_deals[:5]:  # Check first 5
                # Note: Bitrix doesn't have a direct search by title, but we can list recent deals
                # For now, just note that we should check manually
                print(f"  Order {order_id}: Deal {deal_id} marked as missing - may need manual check in Bitrix")
        
        print("=" * 60)
        break

if __name__ == "__main__":
    asyncio.run(check_missing_deals())

