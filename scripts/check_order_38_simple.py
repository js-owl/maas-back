"""Check order 38 and manually find duplicates"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

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
        print(f"  Bitrix Deal ID (in DB): {order.bitrix_deal_id}")
        print(f"  Title pattern: Order #38 - {order.service_id}\n")
        
        # Try to get the deal from DB
        if order.bitrix_deal_id:
            deal = await bitrix_client.get_deal(order.bitrix_deal_id)
            if deal:
                print(f"Deal {order.bitrix_deal_id}:")
                print(f"  Title: {deal.get('TITLE', 'N/A')}")
                print(f"  Created: {deal.get('DATE_CREATE', 'N/A')}")
        
        # Since list_deals isn't working, let's try a different approach:
        # Check deals around the known deal ID (e.g., deal_id-2 to deal_id+10)
        # This is a workaround to find duplicates
        print(f"\nChecking deals around ID {order.bitrix_deal_id}...")
        if order.bitrix_deal_id:
            start_id = max(1, order.bitrix_deal_id - 10)
            end_id = order.bitrix_deal_id + 10
            
            matching_deals = []
            for deal_id in range(start_id, end_id + 1):
                try:
                    deal = await bitrix_client.get_deal(deal_id)
                    if deal:
                        title = deal.get('TITLE', '')
                        if f"Order #38" in title or f"Order #{order.order_id}" in title:
                            matching_deals.append({
                                'id': deal_id,
                                'title': title,
                                'date_create': deal.get('DATE_CREATE', 'N/A')
                            })
                            print(f"  Found: Deal {deal_id} - {title} (Created: {deal.get('DATE_CREATE', 'N/A')})")
                except:
                    pass
            
            print(f"\nFound {len(matching_deals)} deals matching order 38")
            if len(matching_deals) > 1:
                print("\nThese are duplicates that should be cleaned up!")

if __name__ == "__main__":
    asyncio.run(main())









