"""Test crm.status.entity.items API"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.client import bitrix_client

async def test():
    # Test getting stages for category 1 (MaaS)
    entity_id = "DEAL_STAGE_1"
    payload = {"entityId": entity_id}
    
    print(f"Testing crm.status.entity.items with entityId: {entity_id}")
    resp = await bitrix_client._post("crm.status.entity.items", payload)
    
    if resp:
        print(f"Response: {resp}")
        if resp.get("result"):
            stages = resp.get("result")
            print(f"\nFound {len(stages)} stages:")
            for stage in stages:
                print(f"  - {stage.get('NAME')} (ID: {stage.get('STATUS_ID')})")
        else:
            print("No result in response")
    else:
        print("No response")

if __name__ == "__main__":
    asyncio.run(test())


