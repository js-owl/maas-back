"""Reset deal IDs and re-queue orders for new Bitrix instance"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.database import get_db
from backend import models
from sqlalchemy import select, update
from backend.bitrix.sync_service import bitrix_sync_service
from backend.bitrix.funnel_manager import funnel_manager

async def reset_and_requeue():
    print("=" * 60)
    print("Resetting Deals for New Bitrix Instance")
    print("=" * 60)
    
    # 1. Verify new Bitrix instance
    print("\n1. Verifying New Bitrix Instance:")
    await funnel_manager.ensure_maas_funnel()
    if funnel_manager.is_initialized():
        print(f"   ✅ MaaS funnel initialized")
        print(f"   Category ID: {funnel_manager.get_category_id()}")
    else:
        print("   ❌ Failed to initialize MaaS funnel")
        return
    
    # 2. Clear old deal IDs
    print("\n2. Clearing Old Deal IDs:")
    async for db in get_db():
        # Get all orders with deal IDs
        result = await db.execute(
            select(models.Order).where(models.Order.bitrix_deal_id.isnot(None))
        )
        orders = result.scalars().all()
        
        print(f"   Found {len(orders)} orders with deal IDs")
        
        if orders:
            # Clear deal IDs
            await db.execute(
                update(models.Order)
                .where(models.Order.bitrix_deal_id.isnot(None))
                .values(bitrix_deal_id=None)
            )
            await db.commit()
            print(f"   ✅ Cleared {len(orders)} deal IDs")
        else:
            print("   ℹ️  No orders with deal IDs to clear")
        
        # 3. Re-queue all orders for deal creation
        print("\n3. Re-queuing Orders for Deal Creation:")
        all_orders_result = await db.execute(
            select(models.Order).order_by(models.Order.order_id)
        )
        all_orders = all_orders_result.scalars().all()
        
        print(f"   Found {len(all_orders)} total orders")
        
        queued_count = 0
        error_count = 0
        
        for order in all_orders:
            try:
                # Queue deal creation
                await bitrix_sync_service.queue_deal_creation(
                    db, 
                    order.order_id, 
                    order.user_id, 
                    None,  # file_id - will be handled by worker if needed
                    None   # document_ids
                )
                queued_count += 1
                if queued_count % 10 == 0:
                    print(f"   Queued {queued_count} orders...")
            except Exception as e:
                error_count += 1
                print(f"   ❌ Error queuing order {order.order_id}: {e}")
        
        print(f"\n   ✅ Queued {queued_count} orders")
        if error_count > 0:
            print(f"   ⚠️  {error_count} errors")
        
        break
    
    print("\n" + "=" * 60)
    print("✅ Reset complete! Orders are queued and will be processed by the worker.")
    print("   Check Bitrix MaaS funnel to see new deals being created.")

if __name__ == "__main__":
    asyncio.run(reset_and_requeue())







