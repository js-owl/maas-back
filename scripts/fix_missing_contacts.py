"""Fix missing contacts by clearing invalid bitrix_contact_id and re-queuing contact creation"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.database import get_db
from backend import models
from sqlalchemy import select, update
from backend.bitrix.client import bitrix_client
from backend.bitrix.sync_service import bitrix_sync_service

async def fix_contacts():
    print("=" * 80)
    print("Fixing Missing Bitrix Contacts")
    print("=" * 80)
    
    async for db in get_db():
        # 1. Check all users and identify which contacts are invalid
        print("\n1. Checking users and their contacts:")
        result = await db.execute(
            select(models.User)
            .order_by(models.User.id)
        )
        users = result.scalars().all()
        
        invalid_contacts = []
        valid_contacts = []
        no_contact_id = []
        
        for user in users:
            if user.bitrix_contact_id:
                # Verify contact exists
                try:
                    contact = await bitrix_client.get_contact(user.bitrix_contact_id)
                    if contact:
                        valid_contacts.append((user.id, user.bitrix_contact_id, user.username))
                        print(f"  ✅ User {user.id:3d} | Contact {user.bitrix_contact_id:3d} exists | {user.username}")
                    else:
                        invalid_contacts.append((user.id, user.bitrix_contact_id, user.username))
                        print(f"  ❌ User {user.id:3d} | Contact {user.bitrix_contact_id:3d} NOT FOUND | {user.username}")
                except Exception as e:
                    error_msg = str(e)
                    if "Not found" in error_msg or "400" in error_msg:
                        invalid_contacts.append((user.id, user.bitrix_contact_id, user.username))
                        print(f"  ❌ User {user.id:3d} | Contact {user.bitrix_contact_id:3d} NOT FOUND | {user.username}")
                    else:
                        print(f"  ⚠️  User {user.id:3d} | Contact {user.bitrix_contact_id:3d} | Error: {error_msg} | {user.username}")
            else:
                no_contact_id.append((user.id, user.username))
                print(f"  ⏳ User {user.id:3d} | No contact_id | {user.username}")
        
        print(f"\n   Summary: {len(valid_contacts)} valid, {len(invalid_contacts)} invalid, {len(no_contact_id)} without contact_id")
        
        # 2. Clear invalid contact IDs
        if invalid_contacts:
            print(f"\n2. Clearing invalid contact IDs ({len(invalid_contacts)} users):")
            user_ids_to_clear = [user_id for user_id, _, _ in invalid_contacts]
            await db.execute(
                update(models.User)
                .where(models.User.id.in_(user_ids_to_clear))
                .values(bitrix_contact_id=None)
            )
            await db.commit()
            print(f"   ✅ Cleared invalid contact_id for {len(invalid_contacts)} users")
        
        # 3. Re-queue contact creation for users without valid contacts
        users_to_queue = invalid_contacts + no_contact_id
        if users_to_queue:
            print(f"\n3. Re-queuing contact creation ({len(users_to_queue)} users):")
            queued_count = 0
            error_count = 0
            
            for user_id, _, username in invalid_contacts:
                try:
                    await bitrix_sync_service.queue_contact_creation(db, user_id)
                    queued_count += 1
                    print(f"   ✅ Queued user {user_id} ({username})")
                except Exception as e:
                    error_count += 1
                    print(f"   ❌ Error queuing user {user_id}: {e}")
            
            for user_id, username in no_contact_id:
                try:
                    await bitrix_sync_service.queue_contact_creation(db, user_id)
                    queued_count += 1
                    print(f"   ✅ Queued user {user_id} ({username})")
                except Exception as e:
                    error_count += 1
                    print(f"   ❌ Error queuing user {user_id}: {e}")
            
            print(f"\n   ✅ Queued {queued_count} users")
            if error_count > 0:
                print(f"   ⚠️  {error_count} errors")
        else:
            print("\n3. No users need contact creation queued")
        
        print("\n" + "=" * 80)
        print("✅ Fix complete! Contacts are queued and will be processed by the worker.")
        print("   Check Bitrix to see new contacts being created.")
        print("=" * 80)
        
        break

if __name__ == "__main__":
    asyncio.run(fix_contacts())






