"""Clean up duplicate deals for order 41"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.cleanup_service import bitrix_cleanup_service
from backend.bitrix.client import bitrix_client
from sqlalchemy import select

async def cleanup_order_41():
    """Find and clean up duplicate deals for order 41"""
    import sys
    output_lines = []
    
    def log_print(*args, **kwargs):
        msg = ' '.join(str(arg) for arg in args)
        output_lines.append(msg)
        print(*args, **kwargs)
    
    log_print("=" * 80)
    log_print("CLEANING UP DUPLICATE DEALS FOR ORDER 41")
    log_print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        # Get order 41
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 41)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            log_print("\n❌ Order 41 not found in database!")
            # Write output to file
            with open("cleanup_order_41_result.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(output_lines))
            return
        
        log_print(f"\n📋 Order 41 Details:")
        log_print(f"   Order ID: {order.order_id}")
        log_print(f"   Bitrix Deal ID (stored in DB): {order.bitrix_deal_id}")
        log_print(f"   Status: {order.status}")
        log_print(f"   Created: {order.created_at}")
        log_print(f"   Updated: {order.updated_at}")
        
        if order.created_at and order.updated_at:
            time_diff = (order.updated_at - order.created_at).total_seconds()
            if time_diff > 0:
                log_print(f"   ⚠️  Order was updated {time_diff:.0f} seconds after creation")
                log_print(f"      This might have triggered duplicate deal creation")
        
        # Find all deals for order 41
        log_print(f"\n🔍 Searching for all deals with 'Order #41' in title...")
        matching_deals = await bitrix_cleanup_service.find_duplicate_deals_for_order(
            order_id=41,
            known_deal_id=order.bitrix_deal_id
        )
        
        if not matching_deals:
            log_print(f"   ℹ️  No deals found for order 41")
            # Write output to file
            with open("cleanup_order_41_result.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(output_lines))
            return
        
        log_print(f"\n   ✅ Found {len(matching_deals)} deal(s):")
        for i, deal_info in enumerate(matching_deals, 1):
            deal_id = deal_info.get('ID')
            try:
                deal_id_int = int(deal_id) if deal_id else None
            except (ValueError, TypeError):
                deal_id_int = None
            
            is_stored = (deal_id_int == order.bitrix_deal_id) if deal_id_int and order.bitrix_deal_id else False
            
            log_print(f"\n   Deal {i}:")
            log_print(f"     ID: {deal_id}")
            log_print(f"     Title: {deal_info.get('TITLE', 'N/A')}")
            log_print(f"     Created: {deal_info.get('DATE_CREATE', 'N/A')}")
            log_print(f"     Category ID: {deal_info.get('CATEGORY_ID', 'N/A')}")
            log_print(f"     Stage ID: {deal_info.get('STAGE_ID', 'N/A')}")
            if is_stored:
                log_print(f"     ✓ This is the deal stored in database (KEEP)")
            else:
                log_print(f"     ⚠️  DUPLICATE - not stored in database (DELETE)")
        
        # Identify duplicates (all except the one stored in DB)
        duplicates = []
        for deal_info in matching_deals:
            deal_id = deal_info.get('ID')
            try:
                deal_id_int = int(deal_id) if deal_id else None
            except (ValueError, TypeError):
                deal_id_int = None
            
            if deal_id_int and order.bitrix_deal_id:
                if deal_id_int != order.bitrix_deal_id:
                    duplicates.append(deal_id_int)
            elif not order.bitrix_deal_id:
                # If no deal is stored in DB, we need to keep one and delete others
                # For now, we'll keep the first one found
                if deal_id_int and deal_id_int not in [d for d in duplicates if isinstance(d, int)]:
                    if not duplicates:
                        print(f"\n   ⚠️  No deal stored in DB, but found deals. Will keep first one.")
                    duplicates.append(deal_id_int)
        
        if not duplicates:
            log_print(f"\n✅ No duplicate deals found. All deals are accounted for.")
            # Write output to file
            with open("cleanup_order_41_result.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(output_lines))
            return
        
        log_print(f"\n🗑️  Found {len(duplicates)} duplicate deal(s) to delete:")
        for dup_id in duplicates:
            log_print(f"   - Deal {dup_id}")
        
        # Confirm before deleting
        log_print(f"\n⚠️  WARNING: This will delete {len(duplicates)} deal(s) from Bitrix!")
        log_print(f"   Press Ctrl+C to cancel, or wait 5 seconds to proceed...")
        
        try:
            await asyncio.sleep(5)
        except KeyboardInterrupt:
            log_print(f"\n❌ Cancelled by user")
            # Write output to file
            with open("cleanup_order_41_result.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(output_lines))
            return
        
        # Delete duplicates
        log_print(f"\n🗑️  Deleting duplicate deals...")
        deleted_count = 0
        failed_count = 0
        
        for dup_id in duplicates:
            try:
                # Verify deal exists and matches order 41 before deleting
                deal = await bitrix_client.get_deal(dup_id)
                if deal:
                    title = deal.get('TITLE', '')
                    if f"Order #41" in title or f"Order #{41}" in title:
                        success = await bitrix_client.delete_deal(dup_id)
                        if success:
                            log_print(f"   ✅ Deleted deal {dup_id}: {title}")
                            deleted_count += 1
                        else:
                            log_print(f"   ❌ Failed to delete deal {dup_id}")
                            failed_count += 1
                    else:
                        log_print(f"   ⚠️  Skipping deal {dup_id}: Title doesn't match order 41 pattern")
                else:
                    log_print(f"   ⚠️  Deal {dup_id} not found in Bitrix (may already be deleted)")
            except Exception as e:
                log_print(f"   ❌ Error deleting deal {dup_id}: {e}")
                failed_count += 1
        
        log_print(f"\n" + "=" * 80)
        log_print(f"SUMMARY")
        log_print(f"=" * 80)
        log_print(f"   Total deals found: {len(matching_deals)}")
        log_print(f"   Duplicates deleted: {deleted_count}")
        log_print(f"   Failed deletions: {failed_count}")
        log_print(f"   Deal kept (stored in DB): {order.bitrix_deal_id}")
        
        if deleted_count > 0:
            log_print(f"\n✅ Successfully cleaned up {deleted_count} duplicate deal(s)!")
        
        # Write output to file
        with open("cleanup_order_41_result.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))

if __name__ == "__main__":
    import sys
    output = []
    
    # Capture print output
    class OutputCapture:
        def write(self, text):
            output.append(text)
            sys.stdout.write(text)
    
    sys.stdout = OutputCapture()
    
    try:
        asyncio.run(cleanup_order_41())
    finally:
        # Write to file
        with open("order_41_cleanup_result.txt", "w", encoding="utf-8") as f:
            f.write("".join(output))

