"""Check if deals are in MaaS funnel"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.bitrix.client import bitrix_client
from backend.database import get_db
from backend import models
from sqlalchemy import select

async def check():
    print("=" * 60)
    print("Checking Deal Categories in Bitrix")
    print("=" * 60)
    
    # Get a few orders with deal IDs
    async for db in get_db():
        result = await db.execute(select(models.Order).limit(5))
        orders = result.scalars().all()
        
        print(f"\nChecking {len(orders)} orders:")
        
        for order in orders:
            if not order.bitrix_deal_id:
                print(f"\n  Order {order.order_id}: No deal ID")
                continue
            
            print(f"\n  Order {order.order_id}:")
            print(f"    Deal ID: {order.bitrix_deal_id}")
            
            # Get deal from Bitrix
            try:
                deal = await bitrix_client.get_deal(order.bitrix_deal_id)
                if deal:
                    category_id = deal.get("CATEGORY_ID") or deal.get("category_id") or "0"
                    stage_id = deal.get("STAGE_ID") or deal.get("stage_id") or "N/A"
                    title = deal.get("TITLE") or deal.get("title") or "N/A"
                    
                    print(f"    Category ID: {category_id}")
                    print(f"    Stage ID: {stage_id}")
                    print(f"    Title: {title}")
                    
                    if category_id == "1" or category_id == 1:
                        print(f"    ✅ In MaaS funnel")
                    else:
                        print(f"    ⚠️  NOT in MaaS funnel (category: {category_id})")
                else:
                    print(f"    ❌ Deal not found in Bitrix")
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        break
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(check())







