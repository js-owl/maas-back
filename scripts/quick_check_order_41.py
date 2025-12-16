"""Quick check for order 41 - minimal dependencies"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def check():
    try:
        from backend.database import AsyncSessionLocal
        from backend import models
        from sqlalchemy import select
        
        print("Checking order 41...")
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(models.Order).where(models.Order.order_id == 41)
            )
            order = result.scalar_one_or_none()
            
            if not order:
                print("Order 41 not found!")
                return
            
            print(f"\nOrder 41:")
            print(f"  Order ID: {order.order_id}")
            print(f"  Bitrix Deal ID: {order.bitrix_deal_id}")
            print(f"  Status: {order.status}")
            print(f"  Created: {order.created_at}")
            print(f"  Updated: {order.updated_at}")
            
            if order.bitrix_deal_id:
                print(f"\nChecking Bitrix for deal {order.bitrix_deal_id}...")
                from backend.bitrix.client import bitrix_client
                deal = await bitrix_client.get_deal(order.bitrix_deal_id)
                if deal:
                    print(f"  Deal found: {deal.get('TITLE', 'N/A')}")
                else:
                    print(f"  Deal not found in Bitrix!")
                
                print(f"\nSearching for duplicate deals...")
                from backend.bitrix.cleanup_service import bitrix_cleanup_service
                duplicates = await bitrix_cleanup_service.find_duplicate_deals_for_order(
                    order_id=41,
                    known_deal_id=order.bitrix_deal_id
                )
                
                if duplicates:
                    print(f"  Found {len(duplicates)} deal(s):")
                    for d in duplicates:
                        print(f"    - Deal {d.get('ID')}: {d.get('TITLE')}")
                else:
                    print(f"  No duplicates found")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check())





