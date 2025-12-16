"""Final verification after container restart"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal, ensure_order_new_columns
from backend import models
from backend.bitrix.funnel_manager import funnel_manager
from sqlalchemy import select
from collections import Counter

async def verify():
    """Final verification"""
    print("=" * 80)
    print("FINAL VERIFICATION AFTER CONTAINER RESTART")
    print("=" * 80)
    
    # 1. Check database columns
    print("\n1. Database Columns:")
    await ensure_order_new_columns()
    print("   ✓ Database columns ensured")
    
    # 2. Check funnel manager
    print("\n2. Funnel Manager:")
    if not funnel_manager.is_initialized():
        await funnel_manager.ensure_maas_funnel()
    print(f"   ✓ Initialized: {funnel_manager.is_initialized()}")
    print(f"   ✓ Category ID: {funnel_manager.get_category_id()}")
    print(f"   ✓ Mapped stages: {len(funnel_manager.get_status_mapping())}")
    
    # 3. Check order statuses
    print("\n3. Order Statuses:")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
        )
        orders = result.scalars().all()
        
        status_counts = Counter()
        for order in orders:
            status_counts[order.status] += 1
        
        print(f"   Total orders: {len(orders)}")
        print(f"   Status distribution:")
        for status, count in sorted(status_counts.items()):
            print(f"     {status}: {count}")
        
        # Check for old statuses
        old_statuses = ['pending', 'processing', 'completed', 'cancelled']
        found_old = [s for s in status_counts.keys() if s in old_statuses]
        if found_old:
            print(f"   ⚠ Found old statuses: {found_old}")
        else:
            print(f"   ✓ No old statuses found (all using Bitrix stage names)")
    
    # 4. Check invalid deals
    print("\n4. Invalid Deals:")
    invalid_deal_ids = [32, 33, 34, 35, 36, 37, 38]
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.in_(invalid_deal_ids))
        )
        invalid_orders = result.scalars().all()
        
        lose_count = sum(1 for o in invalid_orders if o.status == "LOSE")
        print(f"   Invalid deals: {len(invalid_orders)}")
        print(f"   Marked as LOSE: {lose_count}")
        if lose_count == len(invalid_orders):
            print(f"   ✓ All invalid deals marked as LOSE")
        else:
            print(f"   ⚠ Some invalid deals not marked as LOSE")
    
    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(verify())


