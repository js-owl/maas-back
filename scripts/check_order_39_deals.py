"""Check order 39 and find duplicate deals"""
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
        # Get order 39
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 39)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("Order 39 not found!")
            return
        
        print(f"Order 39 details:")
        print(f"  Order ID: {order.order_id}")
        print(f"  User ID: {order.user_id}")
        print(f"  Bitrix Deal ID (in DB): {order.bitrix_deal_id}")
        print(f"  Status: {order.status}")
        print(f"  Created at: {order.created_at}")
        
        # Search for deals with order title pattern
        print(f"\nSearching for deals with title containing 'Order #39'...")
        
        # Get all deals and filter by title
        # Note: Bitrix API doesn't have a direct search, so we'll need to check deals
        # by looking at the deal stored in DB and searching for similar titles
        
        if order.bitrix_deal_id:
            print(f"\nChecking deal {order.bitrix_deal_id}...")
            deal = await bitrix_client.get_deal(order.bitrix_deal_id)
            if deal:
                print(f"  Title: {deal.get('TITLE', 'N/A')}")
                print(f"  Created: {deal.get('DATE_CREATE', 'N/A')}")
                print(f"  Modified: {deal.get('DATE_MODIFY', 'N/A')}")
        
        # We'll need to implement a search or list method to find duplicates
        # For now, let's check if we can list deals and filter

if __name__ == "__main__":
    asyncio.run(main())









