"""Test script to diagnose MaaS funnel creation"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager
from backend.core.config import BITRIX_MAAS_FUNNEL_NAME, BITRIX_MAAS_CATEGORY_ID

async def test():
    print("=" * 60)
    print("Testing MaaS Funnel Creation")
    print("=" * 60)
    
    print(f"\n1. Bitrix Configuration:")
    print(f"   - Configured: {bitrix_client.is_configured()}")
    print(f"   - Base URL: {bitrix_client.base_url}")
    print(f"   - Enabled: {bitrix_client.enabled}")
    
    print(f"\n2. Funnel Configuration:")
    print(f"   - Funnel Name: {BITRIX_MAAS_FUNNEL_NAME}")
    print(f"   - Category ID (env): {BITRIX_MAAS_CATEGORY_ID}")
    
    if not bitrix_client.is_configured():
        print("\n❌ Bitrix is not configured. Cannot test funnel creation.")
        return
    
    print(f"\n3. Testing get_deal_categories():")
    try:
        categories = await bitrix_client.get_deal_categories()
        if categories:
            print(f"   ✅ Found {len(categories)} categories:")
            for cat in categories[:5]:  # Show first 5
                print(f"      - ID: {cat.get('ID')}, Name: {cat.get('NAME')}")
        else:
            print("   ⚠️  No categories returned (might be None or empty)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n4. Testing get_deal_category_by_name('{BITRIX_MAAS_FUNNEL_NAME}'):")
    try:
        category = await bitrix_client.get_deal_category_by_name(BITRIX_MAAS_FUNNEL_NAME)
        if category:
            print(f"   ✅ Found existing category:")
            print(f"      - ID: {category.get('ID')}")
            print(f"      - Name: {category.get('NAME')}")
        else:
            print("   ℹ️  Category not found (will try to create)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n5. Testing create_deal_category():")
    try:
        stages = [
            {"name": "New Order", "sort": 10, "semantics": "P"},
            {"name": "In Production", "sort": 20, "semantics": "P"},
            {"name": "Completed", "sort": 30, "semantics": "S"},
            {"name": "Cancelled", "sort": 40, "semantics": "F"}
        ]
        category_id = await bitrix_client.create_deal_category(BITRIX_MAAS_FUNNEL_NAME, stages)
        if category_id:
            print(f"   ✅ Created category with ID: {category_id}")
        else:
            print("   ❌ Failed to create category (returned None)")
            print("   This could mean:")
            print("      - API returned error")
            print("      - Webhook doesn't have permissions")
            print("      - Category already exists with same name")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n6. Testing ensure_maas_funnel():")
    try:
        result = await funnel_manager.ensure_maas_funnel()
        print(f"   Result: {result}")
        print(f"   Category ID: {funnel_manager.get_category_id()}")
        print(f"   Initialized: {funnel_manager.is_initialized()}")
        if result:
            print("   ✅ Funnel manager initialized successfully")
        else:
            print("   ❌ Funnel manager initialization failed")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test())







