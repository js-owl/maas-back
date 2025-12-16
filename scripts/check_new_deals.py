"""Check if new deals were created"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.database import get_db
from backend import models
from sqlalchemy import select

async def check():
    print("=" * 60)
    print("Checking New Deals")
    print("=" * 60)
    
    async for db in get_db():
        # Count orders with and without deal IDs
        all_orders_result = await db.execute(select(models.Order))
        all_orders = all_orders_result.scalars().all()
        
        orders_with_deals = [o for o in all_orders if o.bitrix_deal_id]
        orders_without_deals = [o for o in all_orders if not o.bitrix_deal_id]
        
        print(f"\nTotal orders: {len(all_orders)}")
        print(f"Orders with Bitrix deal ID: {len(orders_with_deals)}")
        print(f"Orders without Bitrix deal ID: {len(orders_without_deals)}")
        
        if orders_with_deals:
            print(f"\nFirst 10 orders with deal IDs:")
            for o in orders_with_deals[:10]:
                print(f"  Order {o.order_id}: deal_id={o.bitrix_deal_id}, status={o.status}")
        
        break
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(check())







