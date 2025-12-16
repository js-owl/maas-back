"""Run cleanup for order 41 and write results to file"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

async def main():
    output = []
    output.append("=" * 80)
    output.append("CLEANUP ORDER 41 DUPLICATE DEALS")
    output.append(f"Run at: {datetime.now()}")
    output.append("=" * 80)
    
    try:
        from backend.database import AsyncSessionLocal
        from backend import models
        from backend.bitrix.cleanup_service import bitrix_cleanup_service
        from backend.bitrix.client import bitrix_client
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            # Get order 41
            result = await db.execute(
                select(models.Order).where(models.Order.order_id == 41)
            )
            order = result.scalar_one_or_none()
            
            if not order:
                output.append("\n❌ Order 41 not found in database!")
                return "\n".join(output)
            
            output.append(f"\n📋 Order 41 Details:")
            output.append(f"   Order ID: {order.order_id}")
            output.append(f"   Bitrix Deal ID (stored in DB): {order.bitrix_deal_id}")
            output.append(f"   Status: {order.status}")
            output.append(f"   Created: {order.created_at}")
            output.append(f"   Updated: {order.updated_at}")
            
            if order.created_at and order.updated_at:
                time_diff = (order.updated_at - order.created_at).total_seconds()
                if time_diff > 0:
                    output.append(f"   ⚠️  Order was updated {time_diff:.0f} seconds after creation")
            
            # Find all deals
            output.append(f"\n🔍 Searching for all deals with 'Order #41' in title...")
            matching_deals = await bitrix_cleanup_service.find_duplicate_deals_for_order(
                order_id=41,
                known_deal_id=order.bitrix_deal_id
            )
            
            if not matching_deals:
                output.append(f"   ℹ️  No deals found for order 41")
                return "\n".join(output)
            
            output.append(f"\n   ✅ Found {len(matching_deals)} deal(s):")
            duplicates = []
            
            for i, deal_info in enumerate(matching_deals, 1):
                deal_id = deal_info.get('ID')
                try:
                    deal_id_int = int(deal_id) if deal_id else None
                except (ValueError, TypeError):
                    deal_id_int = None
                
                is_stored = (deal_id_int == order.bitrix_deal_id) if deal_id_int and order.bitrix_deal_id else False
                
                output.append(f"\n   Deal {i}:")
                output.append(f"     ID: {deal_id}")
                output.append(f"     Title: {deal_info.get('TITLE', 'N/A')}")
                output.append(f"     Created: {deal_info.get('DATE_CREATE', 'N/A')}")
                output.append(f"     Category ID: {deal_info.get('CATEGORY_ID', 'N/A')}")
                output.append(f"     Stage ID: {deal_info.get('STAGE_ID', 'N/A')}")
                
                if is_stored:
                    output.append(f"     ✓ This is the deal stored in database (KEEP)")
                else:
                    output.append(f"     ⚠️  DUPLICATE - not stored in database (DELETE)")
                    if deal_id_int:
                        duplicates.append(deal_id_int)
            
            if not duplicates:
                output.append(f"\n✅ No duplicate deals found. All deals are accounted for.")
                return "\n".join(output)
            
            output.append(f"\n🗑️  Found {len(duplicates)} duplicate deal(s) to delete:")
            for dup_id in duplicates:
                output.append(f"   - Deal {dup_id}")
            
            output.append(f"\n⚠️  WARNING: This will delete {len(duplicates)} deal(s) from Bitrix!")
            output.append(f"   Proceeding with deletion...")
            
            # Delete duplicates
            deleted_count = 0
            failed_count = 0
            
            for dup_id in duplicates:
                try:
                    deal = await bitrix_client.get_deal(dup_id)
                    if deal:
                        title = deal.get('TITLE', '')
                        if f"Order #41" in title or f"Order #{41}" in title:
                            success = await bitrix_client.delete_deal(dup_id)
                            if success:
                                output.append(f"   ✅ Deleted deal {dup_id}: {title}")
                                deleted_count += 1
                            else:
                                output.append(f"   ❌ Failed to delete deal {dup_id}")
                                failed_count += 1
                        else:
                            output.append(f"   ⚠️  Skipping deal {dup_id}: Title doesn't match")
                    else:
                        output.append(f"   ⚠️  Deal {dup_id} not found in Bitrix")
                except Exception as e:
                    output.append(f"   ❌ Error deleting deal {dup_id}: {e}")
                    failed_count += 1
            
            output.append(f"\n" + "=" * 80)
            output.append(f"SUMMARY")
            output.append(f"=" * 80)
            output.append(f"   Total deals found: {len(matching_deals)}")
            output.append(f"   Duplicates deleted: {deleted_count}")
            output.append(f"   Failed deletions: {failed_count}")
            output.append(f"   Deal kept (stored in DB): {order.bitrix_deal_id}")
            
            if deleted_count > 0:
                output.append(f"\n✅ Successfully cleaned up {deleted_count} duplicate deal(s)!")
            
    except Exception as e:
        output.append(f"\n❌ Error: {e}")
        import traceback
        output.append(traceback.format_exc())
    
    result_text = "\n".join(output)
    
    # Write to file
    with open("cleanup_order_41_result.txt", "w", encoding="utf-8") as f:
        f.write(result_text)
    
    # Also print
    print(result_text)
    
    return result_text

if __name__ == "__main__":
    asyncio.run(main())





