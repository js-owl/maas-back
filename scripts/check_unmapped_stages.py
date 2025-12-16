"""Check orders with unmapped Bitrix stages"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager
from sqlalchemy import select

async def check():
    """Check orders with unmapped stages"""
    async with AsyncSessionLocal() as db:
        # Ensure funnel manager is initialized
        if not funnel_manager.is_initialized():
            await funnel_manager.ensure_maas_funnel()
        
        # Get all orders with Bitrix deals
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        print("=" * 100)
        print("ORDERS WITH UNMAPPED BITRIX STAGES")
        print("=" * 100)
        print("\nThese orders have Bitrix stages that are not mapped to order statuses:\n")
        
        unmapped = []
        for order in orders:
            try:
                deal_data = await bitrix_client.get_deal(order.bitrix_deal_id)
                if not deal_data:
                    continue
                
                bitrix_stage = deal_data.get("STAGE_ID") or deal_data.get("stage_id", "N/A")
                
                # Check if stage is mapped
                mapped_status = None
                if funnel_manager.is_initialized():
                    mapped_status = funnel_manager.get_status_for_stage_id(bitrix_stage)
                
                if not mapped_status:
                    unmapped.append({
                        "order_id": order.order_id,
                        "deal_id": order.bitrix_deal_id,
                        "db_status": order.status,
                        "bitrix_stage": bitrix_stage,
                        "updated_at": order.updated_at
                    })
            except:
                pass
        
        if unmapped:
            print(f"{'Order ID':<10} {'Deal ID':<10} {'DB Status':<15} {'Bitrix Stage':<30} {'Updated':<20}")
            print("-" * 100)
            for item in unmapped:
                print(f"{item['order_id']:<10} {item['deal_id']:<10} {item['db_status']:<15} {item['bitrix_stage']:<30} {str(item['updated_at'])[:19]}")
            
            print(f"\n\nTotal: {len(unmapped)} orders with unmapped stages")
            print("\nThese stages need to be added to the funnel mapping:")
            unique_stages = set(item['bitrix_stage'] for item in unmapped)
            for stage in sorted(unique_stages):
                print(f"  - {stage}")
        else:
            print("No orders with unmapped stages found.")
        
        print("\n" + "=" * 100)
        print("CURRENT FUNNEL MAPPING")
        print("=" * 100)
        if funnel_manager.is_initialized():
            status_mapping = funnel_manager.get_status_mapping()
            print("\nMapped stages:")
            for stage, status in status_mapping.items():
                print(f"  {stage} → {status}")

if __name__ == "__main__":
    asyncio.run(check())


