"""Check and initialize MaaS funnel"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.bitrix.funnel_manager import funnel_manager

async def check():
    print("=" * 80)
    print("Checking MaaS Funnel Status")
    print("=" * 80)
    
    print(f"\nFunnel Initialized: {funnel_manager.is_initialized()}")
    print(f"Category ID: {funnel_manager.get_category_id()}")
    
    if not funnel_manager.is_initialized():
        print("\nInitializing MaaS funnel...")
        success = await funnel_manager.ensure_maas_funnel()
        if success:
            print(f"✓ Funnel initialized with category ID: {funnel_manager.get_category_id()}")
        else:
            print("✗ Failed to initialize funnel")
    else:
        print(f"\n✓ Funnel already initialized")
        print(f"  Category ID: {funnel_manager.get_category_id()}")
        print(f"  Stage mapping: {funnel_manager.get_stage_mapping()}")
        print(f"  Status mapping: {funnel_manager.get_status_mapping()}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(check())






