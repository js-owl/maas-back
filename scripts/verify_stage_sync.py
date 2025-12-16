"""Verify stage sync is working by checking specific orders"""
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
    """Verify stage sync"""
    print("=" * 100)
    print("STAGE SYNC VERIFICATION")
    print("=" * 100)
    
    async with AsyncSessionLocal() as db:
        # Check order 20 (was recently updated)
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 20)
        )
        order_20 = result.scalar_one_or_none()
        
        if order_20:
            print(f"\nOrder 20 (Recently Updated):")
            print(f"  DB Status: {order_20.status}")
            print(f"  Deal ID: {order_20.bitrix_deal_id}")
            print(f"  Updated: {order_20.updated_at}")
            
            # Get current Bitrix stage
            try:
                deal_data = await bitrix_client.get_deal(order_20.bitrix_deal_id)
                if deal_data:
                    bitrix_stage = deal_data.get("STAGE_ID") or deal_data.get("stage_id", "N/A")
                    stage_name = deal_data.get("STAGE_NAME") or deal_data.get("stageName", "N/A")
                    print(f"  Bitrix Stage ID: {bitrix_stage}")
                    print(f"  Bitrix Stage Name: {stage_name}")
                    
                    # Check if funnel manager can map it
                    if funnel_manager.is_initialized():
                        mapped_status = funnel_manager.get_status_for_stage_id(bitrix_stage)
                        print(f"  Mapped Status: {mapped_status}")
                        if mapped_status == order_20.status:
                            print(f"  ✓ Status matches mapped status!")
                        else:
                            print(f"  ⚠ Status mismatch: DB has '{order_20.status}', mapped is '{mapped_status}'")
            except Exception as e:
                print(f"  ✗ Error getting deal: {e}")
        
        # Check a few more orders
        print(f"\n" + "=" * 100)
        print("Checking Multiple Orders:")
        print("=" * 100)
        
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.updated_at.desc())
            .limit(5)
        )
        recent_orders = result.scalars().all()
        
        print(f"\n{'Order ID':<10} {'DB Status':<15} {'Deal ID':<10} {'Bitrix Stage':<20} {'Synced':<10}")
        print("-" * 100)
        
        for order in recent_orders:
            try:
                deal_data = await bitrix_client.get_deal(order.bitrix_deal_id)
                if deal_data:
                    bitrix_stage = deal_data.get("STAGE_ID") or deal_data.get("stage_id", "N/A")
                    
                    # Map stage to status
                    mapped_status = None
                    if funnel_manager.is_initialized():
                        mapped_status = funnel_manager.get_status_for_stage_id(bitrix_stage)
                    
                    synced = "✓" if mapped_status == order.status else "✗"
                    print(f"{order.order_id:<10} {order.status:<15} {order.bitrix_deal_id or 'N/A':<10} {bitrix_stage:<20} {synced:<10}")
            except:
                print(f"{order.order_id:<10} {order.status:<15} {order.bitrix_deal_id or 'N/A':<10} {'Error':<20} {'?':<10}")

if __name__ == "__main__":
    asyncio.run(verify())


