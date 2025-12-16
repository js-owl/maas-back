"""Attach files to all orders that have file_id but no file attached in Bitrix"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from backend.bitrix.sync_service import bitrix_sync_service
from backend.files.service import get_file_by_id
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        # Get all orders with Bitrix deals and file_id
        result = await db.execute(
            select(models.Order)
            .where(
                models.Order.bitrix_deal_id.isnot(None),
                models.Order.file_id.isnot(None)
            )
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        print(f"Found {len(orders)} orders with Bitrix deals and file_id")
        print("Checking which ones need file attachment...\n")
        
        needs_attachment = []
        
        for order in orders:
            # Check if file is already attached
            deal = await bitrix_client.get_deal(order.bitrix_deal_id)
            if deal:
                file_field_code = bitrix_client.deal_file_field_code
                file_value = deal.get(file_field_code)
                if not file_value:
                    # File not attached, check if file exists
                    file_record = await get_file_by_id(db, order.file_id)
                    if file_record and file_record.file_path:
                        file_path = Path(file_record.file_path)
                        if file_path.exists():
                            needs_attachment.append((order, file_record))
                            print(f"Order {order.order_id} (Deal {order.bitrix_deal_id}): Needs attachment - {file_record.filename}")
                        else:
                            print(f"Order {order.order_id}: File path doesn't exist: {file_path}")
                    else:
                        print(f"Order {order.order_id}: File record not found")
        
        print(f"\nFound {len(needs_attachment)} orders that need file attachment")
        
        if needs_attachment:
            print("\nAttaching files directly (not via queue)...")
            success_count = 0
            fail_count = 0
            
            for order, file_record in needs_attachment:
                try:
                    file_path = Path(file_record.file_path)
                    success = await bitrix_client.attach_file_to_deal(
                        order.bitrix_deal_id,
                        str(file_path),
                        file_record.original_filename or file_record.filename
                    )
                    if success:
                        success_count += 1
                        print(f"✓ Order {order.order_id}: File attached")
                    else:
                        fail_count += 1
                        print(f"✗ Order {order.order_id}: Failed to attach file")
                except Exception as e:
                    fail_count += 1
                    print(f"✗ Order {order.order_id}: Error - {e}")
            
            print(f"\nCompleted:")
            print(f"  Success: {success_count}")
            print(f"  Failed: {fail_count}")

if __name__ == "__main__":
    asyncio.run(main())









