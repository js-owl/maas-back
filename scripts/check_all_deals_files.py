"""Check all deals in Bitrix and identify which ones don't have model files attached"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.database import get_db
from backend import models
from sqlalchemy import select
from backend.bitrix.client import bitrix_client
from backend.files.service import get_file_by_id
from pathlib import Path

async def check_all_deals():
    print("=" * 80)
    print("Checking All Deals for Model Files")
    print("=" * 80)
    
    async for db in get_db():
        # Get all orders with deal IDs
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        print(f"\nFound {len(orders)} orders with Bitrix deals\n")
        
        deals_with_files = []
        deals_without_files = []
        deals_missing_file_in_db = []
        deals_file_not_on_disk = []
        deals_file_attach_failed = []
        errors = []
        
        for order in orders:
            try:
                # Get deal from Bitrix
                deal = await bitrix_client.get_deal(order.bitrix_deal_id)
                if not deal:
                    errors.append((order.order_id, order.bitrix_deal_id, "Deal not found in Bitrix"))
                    continue
                
                deal_title = deal.get("TITLE", "N/A")
                file_field_code = bitrix_client.deal_file_field_code
                file_value = deal.get(file_field_code)
                
                # Check if file is attached in Bitrix
                has_file_in_bitrix = bool(file_value)
                
                # Check if order has file_id in database
                has_file_in_db = order.file_id is not None
                
                # If order has file_id, check if file exists on disk
                file_exists_on_disk = False
                file_record = None
                if has_file_in_db:
                    file_record = await get_file_by_id(db, order.file_id)
                    if file_record and file_record.file_path:
                        file_path = Path(file_record.file_path)
                        file_exists_on_disk = file_path.exists()
                
                # Categorize the deal
                status = []
                if has_file_in_bitrix:
                    status.append("✅ File attached")
                    deals_with_files.append((order.order_id, order.bitrix_deal_id, deal_title))
                else:
                    status.append("❌ No file attached")
                    
                    if not has_file_in_db:
                        status.append("(Order has no file_id in DB)")
                        deals_missing_file_in_db.append((order.order_id, order.bitrix_deal_id, deal_title))
                    elif not file_exists_on_disk:
                        status.append(f"(File not on disk: {file_record.file_path if file_record else 'N/A'})")
                        deals_file_not_on_disk.append((order.order_id, order.bitrix_deal_id, deal_title, file_record.file_path if file_record else None))
                    else:
                        status.append("(File exists but not attached - may need manual attachment)")
                        deals_file_attach_failed.append((order.order_id, order.bitrix_deal_id, deal_title, order.file_id))
                
                # Print status for each deal
                print(f"Order {order.order_id:3d} | Deal {order.bitrix_deal_id:3d} | {', '.join(status)}")
                if has_file_in_db and file_record:
                    print(f"           |        |   File ID: {order.file_id}, Path: {file_record.file_path}")
                
            except Exception as e:
                error_msg = str(e)
                errors.append((order.order_id, order.bitrix_deal_id, error_msg))
                print(f"Order {order.order_id:3d} | Deal {order.bitrix_deal_id:3d} | ⚠️  Error: {error_msg}")
        
        # Print summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total deals checked: {len(orders)}")
        print(f"✅ Deals with files attached: {len(deals_with_files)}")
        print(f"❌ Deals without files: {len(deals_without_files)}")
        print(f"   - Missing file_id in DB: {len(deals_missing_file_in_db)}")
        print(f"   - File not on disk: {len(deals_file_not_on_disk)}")
        print(f"   - File exists but not attached: {len(deals_file_attach_failed)}")
        print(f"⚠️  Errors: {len(errors)}")
        
        # Detailed breakdown
        if deals_missing_file_in_db:
            print(f"\n{'=' * 80}")
            print(f"Deals Missing File in Database ({len(deals_missing_file_in_db)}):")
            print(f"{'=' * 80}")
            for order_id, deal_id, title in deals_missing_file_in_db:
                print(f"  Order {order_id} | Deal {deal_id} | {title}")
        
        if deals_file_not_on_disk:
            print(f"\n{'=' * 80}")
            print(f"Deals with Files Not on Disk ({len(deals_file_not_on_disk)}):")
            print(f"{'=' * 80}")
            for order_id, deal_id, title, file_path in deals_file_not_on_disk:
                print(f"  Order {order_id} | Deal {deal_id} | {title}")
                print(f"    File path: {file_path}")
        
        if deals_file_attach_failed:
            print(f"\n{'=' * 80}")
            print(f"Deals with Files That Should Be Attached ({len(deals_file_attach_failed)}):")
            print(f"{'=' * 80}")
            for order_id, deal_id, title, file_id in deals_file_attach_failed:
                print(f"  Order {order_id} | Deal {deal_id} | File ID: {file_id} | {title}")
            print(f"\n  These files exist and should be attached. Run attach_files_to_existing_deals.py to fix.")
        
        if errors:
            print(f"\n{'=' * 80}")
            print(f"Errors ({len(errors)}):")
            print(f"{'=' * 80}")
            for order_id, deal_id, error in errors[:10]:  # Show first 10
                print(f"  Order {order_id} | Deal {deal_id} | {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")
        
        print("\n" + "=" * 80)
        break

if __name__ == "__main__":
    asyncio.run(check_all_deals())






