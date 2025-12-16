"""Verify orders that were updated"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager
from sqlalchemy import select

async def verify():
    """Verify updated orders"""
    async with AsyncSessionLocal() as db:
        # Ensure funnel is initialized
        if not funnel_manager.is_initialized():
            await funnel_manager.ensure_maas_funnel()
        
        # Check the recently updated orders
        order_ids = [14, 15, 17, 41]
        
        print("=" * 100)
        print("VERIFYING UPDATED ORDERS")
        print("=" * 100)
        
        for order_id in order_ids:
            result = await db.execute(
                select(models.Order).where(models.Order.order_id == order_id)
            )
            order = result.scalar_one_or_none()
            
            if order:
                print(f"\nOrder {order_id}:")
                print(f"  DB Status: {order.status}")
                print(f"  Deal ID: {order.bitrix_deal_id}")
                print(f"  Updated: {order.updated_at}")
                
                # Get Bitrix stage
                try:
                    deal_data = await bitrix_client.get_deal(order.bitrix_deal_id)
                    if deal_data:
                        bitrix_stage = deal_data.get("STAGE_ID") or deal_data.get("stage_id", "N/A")
                        stage_name = deal_data.get("STAGE_NAME") or deal_data.get("stageName", "N/A")
                        print(f"  Bitrix Stage ID: {bitrix_stage}")
                        print(f"  Bitrix Stage Name: {stage_name}")
                        
                        # Check mapping
                        mapped_status = funnel_manager.get_status_for_stage_id(bitrix_stage)
                        print(f"  Mapped Status: {mapped_status}")
                        
                        if mapped_status == order.status:
                            print(f"  ✓ Status matches!")
                        else:
                            print(f"  ⚠ Status mismatch: DB has '{order.status}', mapped is '{mapped_status}'")
                except Exception as e:
                    print(f"  ✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify())


