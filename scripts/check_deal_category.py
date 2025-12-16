"""Check if a deal is in MaaS funnel"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager

async def check_deal(deal_id: int):
    await funnel_manager.ensure_maas_funnel()
    maas_category_id = funnel_manager.get_category_id()
    
    deal_info = await bitrix_client.get_deal(deal_id)
    if deal_info:
        category_id = deal_info.get('CATEGORY_ID')
        print(f"Deal {deal_id}:")
        print(f"  Category ID: {category_id}")
        print(f"  MaaS Category ID: {maas_category_id}")
        print(f"  In MaaS funnel: {str(category_id) == str(maas_category_id)}")
        print(f"  Stage: {deal_info.get('STAGE_ID')}")
        print(f"  Title: {deal_info.get('TITLE')}")
    else:
        print(f"Deal {deal_id} not found")

if __name__ == "__main__":
    # Check deal 18 (order 33)
    asyncio.run(check_deal(18))
    print()
    # Check deals 13-17 (orders 28-32)
    for deal_id in [13, 14, 15, 16, 17]:
        asyncio.run(check_deal(deal_id))


