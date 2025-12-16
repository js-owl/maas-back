"""Check Bitrix sync status"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        # Check orders with Bitrix deals
        orders_result = await db.execute(
            select(models.Order).where(models.Order.bitrix_deal_id.isnot(None))
        )
        orders_with_deals = orders_result.scalars().all()
        
        # Check users with Bitrix contacts
        users_result = await db.execute(
            select(models.User).where(models.User.bitrix_contact_id.isnot(None))
        )
        users_with_contacts = users_result.scalars().all()
        
        # Check total orders and users
        all_orders_result = await db.execute(select(models.Order))
        all_orders = all_orders_result.scalars().all()
        
        all_users_result = await db.execute(select(models.User))
        all_users = all_users_result.scalars().all()
        
        print("="*60)
        print("Bitrix Sync Status")
        print("="*60)
        print(f"Total Orders: {len(all_orders)}")
        print(f"Orders with Bitrix deals: {len(orders_with_deals)}")
        print(f"Orders without Bitrix deals: {len(all_orders) - len(orders_with_deals)}")
        print()
        print(f"Total Users: {len(all_users)}")
        print(f"Users with Bitrix contacts: {len(users_with_contacts)}")
        print(f"Users without Bitrix contacts: {len(all_users) - len(users_with_contacts)}")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(main())


