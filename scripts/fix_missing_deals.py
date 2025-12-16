"""Fix missing deals by clearing bitrix_deal_id and re-queuing for new Bitrix instance"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.database import get_db
from backend import models
from sqlalchemy import select, update
from backend.bitrix.sync_service import bitrix_sync_service

async def fix_missing_deals():
    print("=" * 60)
    print("Fixing Missing Deals")
    print("=" * 60)
    
    # Deal IDs that are missing in Bitrix
    missing_deal_ids = [20, 21, 22, 23, 24, 25, 26, 27, 28, 30, 31]
    
    async for db in get_db():
        # 1. Find orders with missing deal IDs
        print("\n1. Finding orders with missing deal IDs:")
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.in_(missing_deal_ids))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        print(f"   Found {len(orders)} orders with missing deal IDs")
        for order in orders:
            print(f"   Order {order.order_id}: Deal ID {order.bitrix_deal_id}")
        
        if not orders:
            print("   No orders found to fix")
            break
        
        # 2. Clear bitrix_deal_id for these orders
        print("\n2. Clearing bitrix_deal_id for missing deals:")
        order_ids = [order.order_id for order in orders]
        await db.execute(
            update(models.Order)
            .where(models.Order.order_id.in_(order_ids))
            .values(bitrix_deal_id=None)
        )
        await db.commit()
        print(f"   ✅ Cleared bitrix_deal_id for {len(orders)} orders")
        
        # 3. Re-queue these orders for deal creation
        print("\n3. Re-queuing orders for deal creation:")
        queued_count = 0
        error_count = 0
        
        for order in orders:
            try:
                # Get file_id and document_ids from order
                file_id = order.file_id
                
                # Parse document_ids if it's a JSON string
                document_ids = None
                if hasattr(order, 'document_ids') and order.document_ids:
                    if isinstance(order.document_ids, str):
                        import json
                        try:
                            document_ids = json.loads(order.document_ids)
                        except:
                            document_ids = None
                    else:
                        document_ids = order.document_ids
                
                # Queue deal creation
                await bitrix_sync_service.queue_deal_creation(
                    db, 
                    order.order_id, 
                    order.user_id, 
                    file_id,
                    document_ids
                )
                queued_count += 1
                print(f"   ✅ Queued order {order.order_id} (file_id: {file_id})")
            except Exception as e:
                error_count += 1
                print(f"   ❌ Error queuing order {order.order_id}: {e}")
        
        print(f"\n" + "=" * 60)
        print(f"Summary:")
        print(f"  Orders fixed: {queued_count}")
        if error_count > 0:
            print(f"  Errors: {error_count}")
        print(f"\n✅ Fixed! Orders are queued and will be processed by the worker.")
        print(f"   Check Bitrix MaaS funnel to see new deals being created.")
        print("=" * 60)
        
        break

if __name__ == "__main__":
    asyncio.run(fix_missing_deals())






