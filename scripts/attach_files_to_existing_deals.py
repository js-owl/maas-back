"""Attach files to existing deals that don't have files"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.database import get_db
from backend import models
from sqlalchemy import select
from backend.bitrix.client import bitrix_client
from backend.files.service import get_file_by_id
from pathlib import Path

async def attach_files():
    print("=" * 60)
    print("Attaching Files to Existing Deals")
    print("=" * 60)
    
    async for db in get_db():
        # Get all orders with deal IDs and file IDs
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .where(models.Order.file_id.isnot(None))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        print(f"\nFound {len(orders)} orders with deals and files")
        
        attached_count = 0
        skipped_count = 0
        error_count = 0
        
        for order in orders:
            try:
                # Check if file is already attached
                deal = await bitrix_client.get_deal(order.bitrix_deal_id)
                if not deal:
                    print(f"  Order {order.order_id}: Deal {order.bitrix_deal_id} not found")
                    error_count += 1
                    continue
                
                file_field_code = bitrix_client.deal_file_field_code
                file_value = deal.get(file_field_code)
                
                if file_value:
                    print(f"  Order {order.order_id}: File already attached")
                    skipped_count += 1
                    continue
                
                # Get file record
                file_record = await get_file_by_id(db, order.file_id)
                if not file_record or not file_record.file_path:
                    print(f"  Order {order.order_id}: File record not found")
                    error_count += 1
                    continue
                
                file_path = Path(file_record.file_path)
                if not file_path.exists():
                    print(f"  Order {order.order_id}: File path does not exist: {file_path}")
                    error_count += 1
                    continue
                
                # Attach file
                print(f"  Order {order.order_id}: Attaching file to deal {order.bitrix_deal_id}...")
                file_attached = await bitrix_client.attach_file_to_deal(
                    order.bitrix_deal_id,
                    str(file_path),
                    file_record.original_filename or file_record.filename
                )
                
                if file_attached:
                    print(f"    ✅ File attached successfully")
                    attached_count += 1
                else:
                    print(f"    ❌ Failed to attach file")
                    error_count += 1
                    
            except Exception as e:
                print(f"  Order {order.order_id}: Error - {e}")
                error_count += 1
        
        print(f"\n" + "=" * 60)
        print(f"Summary:")
        print(f"  Attached: {attached_count}")
        print(f"  Skipped (already attached): {skipped_count}")
        print(f"  Errors: {error_count}")
        print("=" * 60)
        
        break

if __name__ == "__main__":
    asyncio.run(attach_files())







