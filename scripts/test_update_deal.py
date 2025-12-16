"""Test updating a deal to MaaS funnel"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager
from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select

async def test_update_deal(deal_id: int, order_id: int):
    """Test updating a deal"""
    # Initialize funnel
    await funnel_manager.ensure_maas_funnel()
    
    if not funnel_manager.is_initialized():
        print("❌ Funnel not initialized")
        return
    
    category_id = funnel_manager.get_category_id()
    print(f"MaaS category ID: {category_id}")
    
    # Get order
    async with AsyncSessionLocal() as db:
        order_result = await db.execute(
            select(models.Order).where(models.Order.order_id == order_id)
        )
        order = order_result.scalar_one_or_none()
        
        if not order:
            print(f"Order {order_id} not found")
            return
        
        # Get current deal info
        print(f"\nGetting current deal {deal_id} info...")
        deal_info = await bitrix_client.get_deal(deal_id)
        if deal_info:
            print(f"Current category: {deal_info.get('CATEGORY_ID')}")
            print(f"Current stage: {deal_info.get('STAGE_ID')}")
        
        # Get stage ID
        stage_id = funnel_manager.get_stage_id_for_status(order.status)
        if not stage_id:
            stage_id = "NEW"
        
        print(f"\nUpdating deal {deal_id}...")
        print(f"  Category ID: {category_id}")
        print(f"  Stage ID: {stage_id}")
        print(f"  Order status: {order.status}")
        
        # Try different formats - Bitrix update might need different format
        # Format 1: Without FIELDS prefix
        print("\nTrying format 1: fields[CATEGORY_ID] (lowercase)...")
        update_fields1 = {
            "fields[CATEGORY_ID]": str(category_id),
            "fields[STAGE_ID]": stage_id
        }
        success1 = await bitrix_client.update_deal(deal_id, update_fields1)
        if success1:
            deal_info = await bitrix_client.get_deal(deal_id)
            if deal_info and str(deal_info.get('CATEGORY_ID')) == str(category_id):
                print(f"✅ Format 1 worked! Category is now: {deal_info.get('CATEGORY_ID')}")
                return
        
        # Format 2: Just CATEGORY_ID
        print("\nTrying format 2: CATEGORY_ID (no prefix)...")
        update_fields2 = {
            "CATEGORY_ID": str(category_id),
            "STAGE_ID": stage_id
        }
        success2 = await bitrix_client.update_deal(deal_id, update_fields2)
        if success2:
            deal_info = await bitrix_client.get_deal(deal_id)
            if deal_info and str(deal_info.get('CATEGORY_ID')) == str(category_id):
                print(f"✅ Format 2 worked! Category is now: {deal_info.get('CATEGORY_ID')}")
                return
        
        # Format 3: FIELDS[...] (original)
        print("\nTrying format 3: FIELDS[CATEGORY_ID] (original)...")
        update_fields3 = {
            "FIELDS[CATEGORY_ID]": str(category_id),
            "FIELDS[STAGE_ID]": stage_id
        }
        success3 = await bitrix_client.update_deal(deal_id, update_fields3)
        
        if success:
            print("✅ Update successful!")
            
            # Verify
            print("\nVerifying update...")
            deal_info = await bitrix_client.get_deal(deal_id)
            if deal_info:
                print(f"New category: {deal_info.get('CATEGORY_ID')}")
                print(f"New stage: {deal_info.get('STAGE_ID')}")
        else:
            print("❌ Update failed")

if __name__ == "__main__":
    # Test with deal 13 (order 28)
    asyncio.run(test_update_deal(13, 28))

