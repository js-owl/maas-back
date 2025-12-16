"""Check for ALL deals matching order 38 with broader search"""
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
        print(f"  Service: {order.service_id}\n")
        
        # Search in a much wider range
        print("Searching for deals in a wider range...")
        
        # Start from deal 1 and go up to 200 (or higher if needed)
        matching_deals = []
        
        # Check deals 1-200
        for deal_id in range(1, 201):
            try:
                deal = await bitrix_client.get_deal(deal_id)
                if deal:
                    title = deal.get('TITLE', '')
                    # Check various patterns
                    if (f"Order #38" in title or 
                        f"Order #{order.order_id}" in title or
                        f"order 38" in title.lower() or
                        (order.service_id and order.service_id.lower() in title.lower() and "38" in title)):
                        matching_deals.append({
                            'id': deal_id,
                            'title': title,
                            'date_create': deal.get('DATE_CREATE', 'N/A'),
                            'category_id': deal.get('CATEGORY_ID', 'N/A'),
                            'stage_id': deal.get('STAGE_ID', 'N/A')
                        })
            except Exception:
                pass
        
        print(f"\nFound {len(matching_deals)} deals matching order 38:")
        for deal in matching_deals:
            print(f"  Deal ID: {deal['id']}, Title: {deal['title']}, Created: {deal['date_create']}, Category: {deal['category_id']}, Stage: {deal['stage_id']}")
        
        if len(matching_deals) > 1:
            print(f"\n⚠️  Found {len(matching_deals)} duplicate deals! Need to clean up.")

if __name__ == "__main__":
    asyncio.run(main())









