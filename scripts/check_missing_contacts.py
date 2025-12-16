"""Check which users don't have Bitrix contacts and why"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.database import get_db
from backend import models
from sqlalchemy import select
from backend.bitrix.client import bitrix_client

async def check_contacts():
    print("=" * 80)
    print("Checking Users and Bitrix Contacts")
    print("=" * 80)
    
    async for db in get_db():
        # Get all users
        result = await db.execute(
            select(models.User)
            .order_by(models.User.id)
        )
        users = result.scalars().all()
        
        print(f"\nFound {len(users)} users in database\n")
        
        users_with_contacts = []
        users_without_contacts = []
        contacts_not_found = []
        contacts_found = []
        
        for user in users:
            has_contact_id = user.bitrix_contact_id is not None
            
            if has_contact_id:
                # Verify contact exists in Bitrix
                try:
                    contact = await bitrix_client.get_contact(user.bitrix_contact_id)
                    if contact:
                        name = contact.get("NAME") or ""
                        last_name = contact.get("LAST_NAME") or ""
                        contact_name = f"{name} {last_name}".strip() or "N/A"
                        email_list = contact.get("EMAIL")
                        if email_list and isinstance(email_list, list) and len(email_list) > 0:
                            contact_email = email_list[0].get("VALUE", "N/A")
                        else:
                            contact_email = "N/A"
                        print(f"  ✅ User {user.id:3d} | Contact {user.bitrix_contact_id:3d} | {user.username} | {contact_name}")
                        contacts_found.append((user.id, user.bitrix_contact_id, user.username))
                        users_with_contacts.append((user.id, user.username))
                    else:
                        print(f"  ❌ User {user.id:3d} | Contact {user.bitrix_contact_id:3d} NOT FOUND | {user.username}")
                        contacts_not_found.append((user.id, user.bitrix_contact_id, user.username))
                except Exception as e:
                    error_msg = str(e)
                    if "Not found" in error_msg or "400" in error_msg or "Bad Request" in error_msg:
                        print(f"  ❌ User {user.id:3d} | Contact {user.bitrix_contact_id:3d} NOT FOUND | {user.username}")
                        contacts_not_found.append((user.id, user.bitrix_contact_id, user.username))
                    else:
                        print(f"  ⚠️  User {user.id:3d} | Contact {user.bitrix_contact_id:3d} | Error: {error_msg} | {user.username}")
            else:
                print(f"  ⏳ User {user.id:3d} | No contact_id | {user.username} | {user.email}")
                users_without_contacts.append((user.id, user.username, user.email, user.full_name))
        
        # Print summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total users: {len(users)}")
        print(f"✅ Users with valid contacts: {len(contacts_found)}")
        print(f"❌ Users with invalid contact_id (not found in Bitrix): {len(contacts_not_found)}")
        print(f"⏳ Users without contact_id: {len(users_without_contacts)}")
        
        if contacts_not_found:
            print(f"\n{'=' * 80}")
            print(f"Users with Invalid Contact IDs ({len(contacts_not_found)}):")
            print(f"{'=' * 80}")
            for user_id, contact_id, username in contacts_not_found:
                print(f"  User {user_id} | Contact ID {contact_id} (not found) | {username}")
            print(f"\n  These users have contact_id set but the contact doesn't exist in Bitrix.")
            print(f"  They were likely created in the old Bitrix instance.")
        
        if users_without_contacts:
            print(f"\n{'=' * 80}")
            print(f"Users Without Bitrix Contacts ({len(users_without_contacts)}):")
            print(f"{'=' * 80}")
            for user_id, username, email, full_name in users_without_contacts[:20]:  # Show first 20
                print(f"  User {user_id:3d} | {username:20s} | {email or 'N/A':30s} | {full_name or 'N/A'}")
            if len(users_without_contacts) > 20:
                print(f"  ... and {len(users_without_contacts) - 20} more users")
            print(f"\n  These users need contacts created in Bitrix.")
        
        print("\n" + "=" * 80)
        break

if __name__ == "__main__":
    asyncio.run(check_contacts())

