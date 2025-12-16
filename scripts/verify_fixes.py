"""Verify that fixes are working correctly"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.funnel_manager import funnel_manager
from backend.bitrix.deal_sync_service import deal_sync_service
from sqlalchemy import select

async def verify():
    """Verify fixes are working"""
    print("=" * 80)
    print("VERIFICATION: FIXES STATUS")
    print("=" * 80)
    
    # 1. Check funnel manager
    print("\n1. Funnel Manager:")
    if funnel_manager.is_initialized():
        print("   ✓ Funnel manager is initialized")
        print(f"   Category ID: {funnel_manager.get_category_id()}")
        print(f"   Stage mapping: {funnel_manager.get_stage_mapping()}")
    else:
        print("   ✗ Funnel manager is NOT initialized")
        print("   Attempting to initialize...")
        success = await funnel_manager.ensure_maas_funnel()
        if success:
            print("   ✓ Funnel manager initialized successfully")
        else:
            print("   ✗ Failed to initialize funnel manager")
    
    # 2. Test sync on a problematic deal
    print("\n2. Testing sync with problematic deals:")
    async with AsyncSessionLocal() as db:
        # Find orders with problematic deal IDs [32, 33, 34, 35, 36, 37, 38]
        problematic_deal_ids = [32, 33, 34, 35, 36, 37, 38]
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.in_(problematic_deal_ids))
            .limit(1)
        )
        test_order = result.scalar_one_or_none()
        
        if test_order:
            print(f"   Testing with Order {test_order.order_id} (Deal {test_order.bitrix_deal_id})")
            # Test stage sync (should handle 400 gracefully)
            stage_result = await deal_sync_service.sync_deal_stage(
                db, test_order.order_id, test_order.bitrix_deal_id
            )
            print(f"   Stage sync result: {stage_result} (should be False, handled gracefully)")
            
            # Test invoice check (should handle 400 gracefully)
            invoice_result = await deal_sync_service.check_and_download_invoice(
                db, test_order.order_id, test_order.bitrix_deal_id
            )
            print(f"   Invoice check result: {invoice_result} (should be False, handled gracefully)")
        else:
            print("   No orders with problematic deal IDs found for testing")
    
    # 3. Test sync on a valid deal
    print("\n3. Testing sync with valid deal:")
    async with AsyncSessionLocal() as db:
        # Find an order with a valid deal ID (not in problematic list)
        result = await db.execute(
            select(models.Order)
            .where(
                models.Order.bitrix_deal_id.isnot(None),
                ~models.Order.bitrix_deal_id.in_([32, 33, 34, 35, 36, 37, 38])
            )
            .limit(1)
        )
        test_order = result.scalar_one_or_none()
        
        if test_order:
            print(f"   Testing with Order {test_order.order_id} (Deal {test_order.bitrix_deal_id})")
            stage_result = await deal_sync_service.sync_deal_stage(
                db, test_order.order_id, test_order.bitrix_deal_id
            )
            print(f"   Stage sync result: {stage_result} (should be True or False based on status)")
        else:
            print("   No valid orders found for testing")
    
    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)
    print("\nExpected behavior:")
    print("  ✓ Funnel manager should be initialized")
    print("  ✓ Invalid deals (400 errors) should be handled gracefully (warnings, not errors)")
    print("  ✓ Valid deals should sync successfully")
    print("  ✓ Sync should continue processing other orders even if some fail")

if __name__ == "__main__":
    asyncio.run(verify())


