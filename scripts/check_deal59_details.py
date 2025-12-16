"""Check deal 59 details and webhook status"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager

async def check():
    print("=" * 80)
    print("Checking Deal 59 Details")
    print("=" * 80)
    
    # Initialize funnel if needed
    if not funnel_manager.is_initialized():
        print("\nInitializing MaaS funnel...")
        await funnel_manager.ensure_maas_funnel()
    
    maas_category_id = funnel_manager.get_category_id()
    print(f"\nMaaS Funnel Category ID: {maas_category_id}")
    
    # Get deal 59
    print("\nFetching deal 59 from Bitrix...")
    result = await bitrix_client.get_deal(59)
    
    if result and result.get("ID"):
        print(f"\nDeal 59 Details:")
        print(f"  ID: {result.get('ID')}")
        print(f"  Title: {result.get('TITLE', 'N/A')}")
        print(f"  Stage: {result.get('STAGE_ID', 'N/A')}")
        print(f"  Category: {result.get('CATEGORY_ID', 'N/A')}")
        print(f"  Amount: {result.get('OPPORTUNITY', 'N/A')}")
        print(f"  Contact: {result.get('CONTACT_ID', 'N/A')}")
        
        deal_category = result.get('CATEGORY_ID')
        if deal_category and maas_category_id:
            if str(deal_category) == str(maas_category_id):
                print(f"\n✓ Deal 59 is in MaaS funnel (category {deal_category})")
                print("  Webhooks for this deal should be processed")
            else:
                print(f"\n✗ Deal 59 is NOT in MaaS funnel")
                print(f"  Deal category: {deal_category}")
                print(f"  MaaS category: {maas_category_id}")
                print("  Webhooks for this deal will be filtered out")
        else:
            print(f"\n⚠ Cannot verify if deal is in MaaS funnel")
    else:
        print("\n✗ Deal 59 not found in Bitrix")
        if result:
            print(f"  Error response: {result}")

if __name__ == "__main__":
    asyncio.run(check())






