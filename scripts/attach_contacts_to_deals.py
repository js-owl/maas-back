"""Attach contacts to all deals that don't have contacts"""
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
        # Get all orders with Bitrix deals
        orders_result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id)
        )
        orders = orders_result.scalars().all()
        
        print(f"Found {len(orders)} orders with Bitrix deals\n")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for order in orders:
            try:
                # Get user
                user_result = await db.execute(
                    select(models.User).where(models.User.id == order.user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    print(f"Order {order.order_id}: User {order.user_id} not found")
                    error_count += 1
                    continue
                
                if not user.bitrix_contact_id:
                    print(f"Order {order.order_id}: User {user.id} doesn't have Bitrix contact")
                    error_count += 1
                    continue
                
                # Check current deal
                deal = await bitrix_client.get_deal(order.bitrix_deal_id)
                if not deal:
                    print(f"Order {order.order_id}: Deal {order.bitrix_deal_id} not found in Bitrix")
                    error_count += 1
                    continue
                
                current_contact_id = deal.get("CONTACT_ID")
                if current_contact_id == str(user.bitrix_contact_id):
                    print(f"Order {order.order_id}: Contact {user.bitrix_contact_id} already attached")
                    skipped_count += 1
                    continue
                
                # Update deal with contact
                update_data = {
                    "FIELDS[CONTACT_ID]": str(user.bitrix_contact_id)
                }
                success = await bitrix_client.update_deal(order.bitrix_deal_id, update_data)
                
                if success:
                    print(f"Order {order.order_id}: Attached contact {user.bitrix_contact_id} to deal {order.bitrix_deal_id}")
                    updated_count += 1
                else:
                    print(f"Order {order.order_id}: Failed to attach contact {user.bitrix_contact_id}")
                    error_count += 1
                    
            except Exception as e:
                print(f"Order {order.order_id}: Error - {e}")
                error_count += 1
        
        print(f"\nSummary:")
        print(f"  Updated: {updated_count}")
        print(f"  Skipped (already attached): {skipped_count}")
        print(f"  Errors: {error_count}")

if __name__ == "__main__":
    asyncio.run(main())









