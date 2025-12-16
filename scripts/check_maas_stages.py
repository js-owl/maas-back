"""Check stages in MaaS funnel"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager
from backend.core.config import BITRIX_MAAS_CATEGORY_ID

async def main():
    print("=" * 70)
    print("Checking MaaS Funnel Stages")
    print("=" * 70)
    
    # Initialize funnel
    await funnel_manager.ensure_maas_funnel()
    
    if not funnel_manager.is_initialized():
        print("❌ MaaS funnel not initialized")
        return
    
    category_id = funnel_manager.get_category_id()
    print(f"\nMaaS Funnel Category ID: {category_id}")
    
    # Get category info from Bitrix
    print("\n[1/3] Getting category info from Bitrix...")
    category_info = await bitrix_client.get_deal_category_by_name("MaaS")
    if category_info:
        print(f"Category Name: {category_info.get('NAME')}")
        print(f"Category ID: {category_info.get('ID')}")
        
        # Check if stages are in category data
        if "STAGES" in category_info:
            stages = category_info["STAGES"]
            print(f"\n[2/3] Found {len(stages)} stages in category data:")
            for stage in stages:
                print(f"  - {stage.get('NAME')} (ID: {stage.get('STATUS_ID')}, Sort: {stage.get('SORT')})")
        else:
            print("  No STAGES in category data")
    
    # Try to get stages using get_category_stages
    print("\n[3/3] Getting stages using get_category_stages method...")
    stages = await bitrix_client.get_category_stages(category_id)
    if stages:
        print(f"Found {len(stages)} stages:")
        for stage in stages:
            print(f"  - {stage.get('NAME')} (ID: {stage.get('STATUS_ID')}, Sort: {stage.get('SORT')})")
    else:
        print("  No stages found")
    
    # Check funnel manager mappings
    print("\n[4/4] Funnel Manager Stage Mappings:")
    print(f"  Stage name to ID mapping: {funnel_manager.stage_name_to_id}")
    print(f"  Order status to stage mapping: {funnel_manager.stage_mapping}")
    print(f"  Status mapping (reverse): {funnel_manager.status_mapping}")
    
    # Test status mapping
    print("\n[5/5] Testing Status Mappings:")
    test_statuses = ["pending", "processing", "completed", "cancelled"]
    for status in test_statuses:
        stage_id = funnel_manager.get_stage_id_for_status(status)
        print(f"  '{status}' -> '{stage_id}'")

if __name__ == "__main__":
    asyncio.run(main())


