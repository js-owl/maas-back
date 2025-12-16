"""Verify deals were moved to MaaS funnel"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager

async def main():
    await funnel_manager.ensure_maas_funnel()
    maas_category_id = funnel_manager.get_category_id()
    
    print(f"MaaS Category ID: {maas_category_id}\n")
    
    # Check deals 13-22
    deals_to_check = list(range(13, 23))
    
    print("Checking deals:")
    print(f"{'Deal ID':<10} {'Category':<10} {'In MaaS':<10} {'Stage':<15}")
    print("-" * 50)
    
    for deal_id in deals_to_check:
        deal_info = await bitrix_client.get_deal(deal_id)
        if deal_info:
            category_id = deal_info.get('CATEGORY_ID')
            stage_id = deal_info.get('STAGE_ID', 'N/A')
            in_maas = str(category_id) == str(maas_category_id)
            status = "✅" if in_maas else "❌"
            print(f"{deal_id:<10} {category_id:<10} {status:<10} {stage_id:<15}")
        else:
            print(f"{deal_id:<10} {'Not found':<10} {'❌':<10} {'N/A':<15}")

if __name__ == "__main__":
    asyncio.run(main())


