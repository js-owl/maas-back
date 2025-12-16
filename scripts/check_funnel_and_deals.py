"""Check funnel initialization and find problematic deal IDs"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager
from sqlalchemy import select

async def check_all():
    """Check funnel and deal IDs"""
    print("=" * 60)
    print("FUNNEL AND DEAL ID CHECK")
    print("=" * 60)
    
    # 1. Check funnel manager
    print("\n1. Funnel Manager Status:")
    print(f"   Initialized: {funnel_manager.is_initialized()}")
    print(f"   Category ID: {funnel_manager.get_category_id()}")
    
    if not funnel_manager.is_initialized():
        print("\n   Attempting to initialize...")
        success = await funnel_manager.ensure_maas_funnel()
        if success:
            print(f"   ✓ Funnel initialized with category ID: {funnel_manager.get_category_id()}")
            print(f"   Stage mapping: {funnel_manager.get_stage_mapping()}")
            print(f"   Status mapping: {funnel_manager.get_status_mapping()}")
        else:
            print("   ✗ Failed to initialize funnel")
    else:
        print(f"   ✓ Funnel already initialized")
        print(f"   Stage mapping: {funnel_manager.get_stage_mapping()}")
        print(f"   Status mapping: {funnel_manager.get_status_mapping()}")
    
    # 2. Check all orders with Bitrix deals
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        print(f"\n2. Checking {len(orders)} orders with Bitrix deals:")
        print(f"   {'Order ID':<10} {'Deal ID':<10} {'Status':<15} {'Deal Exists':<15} {'Error':<30}")
        print(f"   {'-'*10} {'-'*10} {'-'*15} {'-'*15} {'-'*30}")
        
        problematic_deals = []
        valid_deals = []
        
        for order in orders[:20]:  # Check first 20
            deal_id = order.bitrix_deal_id
            try:
                deal_data = await bitrix_client.get_deal(deal_id)
                if deal_data:
                    valid_deals.append((order.order_id, deal_id))
                    print(f"   {order.order_id:<10} {deal_id:<10} {order.status:<15} {'✓':<15} {'':<30}")
                else:
                    problematic_deals.append((order.order_id, deal_id, "Not found"))
                    print(f"   {order.order_id:<10} {deal_id:<10} {order.status:<15} {'✗':<15} {'Not found':<30}")
            except Exception as e:
                error_msg = str(e)[:28]
                problematic_deals.append((order.order_id, deal_id, error_msg))
                print(f"   {order.order_id:<10} {deal_id:<10} {order.status:<15} {'✗':<15} {error_msg:<30}")
        
        if len(orders) > 20:
            print(f"   ... and {len(orders) - 20} more orders")
        
        print(f"\n3. Summary:")
        print(f"   Valid deals: {len(valid_deals)}")
        print(f"   Problematic deals: {len(problematic_deals)}")
        
        if problematic_deals:
            print(f"\n4. Problematic Deal IDs:")
            for order_id, deal_id, error in problematic_deals[:10]:
                print(f"   Order {order_id}: Deal {deal_id} - {error}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(check_all())

