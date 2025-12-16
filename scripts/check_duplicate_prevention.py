"""Check duplicate prevention logic for deals and contacts"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.database import get_db
from backend import models
from sqlalchemy import select
from backend.bitrix.client import bitrix_client

async def check_duplicates():
    print("=" * 80)
    print("Checking Duplicate Prevention Logic")
    print("=" * 80)
    
    async for db in get_db():
        # Check for duplicate deals (same order_id with multiple bitrix_deal_id)
        print("\n1. Checking for duplicate deals (same order_id):")
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        order_deal_map = {}
        duplicates = []
        
        for order in orders:
            if order.order_id in order_deal_map:
                # Found duplicate
                existing_deal_id = order_deal_map[order.order_id]
                duplicates.append((order.order_id, existing_deal_id, order.bitrix_deal_id))
            else:
                order_deal_map[order.order_id] = order.bitrix_deal_id
        
        if duplicates:
            print(f"   ❌ Found {len(duplicates)} orders with duplicate deal IDs:")
            for order_id, deal_id1, deal_id2 in duplicates:
                print(f"      Order {order_id}: Deal {deal_id1} and Deal {deal_id2}")
        else:
            print(f"   ✅ No duplicate deals found ({len(orders)} orders checked)")
        
        # Check for duplicate contacts (same user_id with multiple bitrix_contact_id)
        print("\n2. Checking for duplicate contacts (same user_id):")
        result2 = await db.execute(
            select(models.User)
            .where(models.User.bitrix_contact_id.isnot(None))
            .order_by(models.User.id)
        )
        users = result2.scalars().all()
        
        user_contact_map = {}
        duplicate_contacts = []
        
        for user in users:
            if user.id in user_contact_map:
                # Found duplicate
                existing_contact_id = user_contact_map[user.id]
                duplicate_contacts.append((user.id, existing_contact_id, user.bitrix_contact_id))
            else:
                user_contact_map[user.id] = user.bitrix_contact_id
        
        if duplicate_contacts:
            print(f"   ❌ Found {len(duplicate_contacts)} users with duplicate contact IDs:")
            for user_id, contact_id1, contact_id2 in duplicate_contacts:
                print(f"      User {user_id}: Contact {contact_id1} and Contact {contact_id2}")
        else:
            print(f"   ✅ No duplicate contacts found ({len(users)} users checked)")
        
        # Check for orders without deals that should have them
        print("\n3. Checking orders without deals:")
        result3 = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.is_(None))
            .order_by(models.Order.order_id.desc())
            .limit(10)
        )
        orders_without_deals = result3.scalars().all()
        
        if orders_without_deals:
            print(f"   Found {len(orders_without_deals)} orders without deals (showing up to 10):")
            for order in orders_without_deals:
                print(f"      Order {order.order_id}: Status {order.status}, Created {order.created_at}")
        else:
            print(f"   ✅ All orders have deals")
        
        # Check for users without contacts that should have them
        print("\n4. Checking users without contacts:")
        result4 = await db.execute(
            select(models.User)
            .where(models.User.bitrix_contact_id.is_(None))
            .order_by(models.User.id)
        )
        users_without_contacts = result4.scalars().all()
        
        if users_without_contacts:
            print(f"   Found {len(users_without_contacts)} users without contacts:")
            for user in users_without_contacts:
                print(f"      User {user.id}: {user.username} ({user.email})")
        else:
            print(f"   ✅ All users have contacts")
        
        print("\n" + "=" * 80)
        print("Summary:")
        print(f"  Orders with deals: {len(orders)}")
        print(f"  Users with contacts: {len(users)}")
        print(f"  Duplicate deals: {len(duplicates)}")
        print(f"  Duplicate contacts: {len(duplicate_contacts)}")
        print("=" * 80)
        
        break

if __name__ == "__main__":
    asyncio.run(check_duplicates())






