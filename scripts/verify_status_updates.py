"""Verify order statuses were updated correctly"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from sqlalchemy import select
from collections import Counter

async def verify():
    """Verify status updates"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
        )
        orders = result.scalars().all()
        
        print("=" * 100)
        print("VERIFYING ORDER STATUS UPDATES")
        print("=" * 100)
        
        matches = 0
        mismatches = []
        status_counts = Counter()
        
        for order in orders:
            try:
                deal_data = await bitrix_client.get_deal(order.bitrix_deal_id)
                if deal_data:
                    bitrix_stage = deal_data.get("STAGE_ID") or deal_data.get("stage_id", "")
                    expected_status = bitrix_stage.replace("C1:", "") if bitrix_stage.startswith("C1:") else bitrix_stage
                    
                    status_counts[order.status] += 1
                    
                    if order.status == expected_status:
                        matches += 1
                    else:
                        mismatches.append({
                            "order_id": order.order_id,
                            "db_status": order.status,
                            "expected": expected_status,
                            "bitrix_stage": bitrix_stage
                        })
            except:
                pass
        
        print(f"\nTotal orders: {len(orders)}")
        print(f"✓ Matches: {matches}")
        print(f"✗ Mismatches: {len(mismatches)}")
        
        print(f"\nStatus distribution:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        
        if mismatches:
            print(f"\n⚠ Mismatches:")
            for mm in mismatches[:10]:
                print(f"  Order {mm['order_id']}: DB has '{mm['db_status']}', expected '{mm['expected']}' (Bitrix: {mm['bitrix_stage']})")
        
        print("\n" + "=" * 100)

if __name__ == "__main__":
    asyncio.run(verify())


