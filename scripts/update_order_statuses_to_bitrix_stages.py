"""Update order statuses in DB to match Bitrix stage names (without C1: prefix)"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from sqlalchemy import select, update

async def update_statuses():
    """Update order statuses to match Bitrix stages"""
    async with AsyncSessionLocal() as db:
        # Get all orders with Bitrix deals
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
        )
        orders = result.scalars().all()
        
        print("=" * 100)
        print("UPDATING ORDER STATUSES TO MATCH BITRIX STAGES")
        print("=" * 100)
        print(f"\nProcessing {len(orders)} orders...\n")
        
        updated_count = 0
        error_count = 0
        skipped_count = 0
        
        print(f"{'Order ID':<10} {'Old Status':<20} {'Deal ID':<10} {'Bitrix Stage':<25} {'New Status':<25} {'Result':<10}")
        print("-" * 100)
        
        for order in orders:
            try:
                # Get deal from Bitrix
                deal_data = await bitrix_client.get_deal(order.bitrix_deal_id)
                if not deal_data:
                    print(f"{order.order_id:<10} {order.status:<20} {order.bitrix_deal_id:<10} {'NOT FOUND':<25} {'N/A':<25} {'SKIPPED':<10}")
                    skipped_count += 1
                    continue
                
                bitrix_stage = deal_data.get("STAGE_ID") or deal_data.get("stage_id", "")
                
                if not bitrix_stage:
                    print(f"{order.order_id:<10} {order.status:<20} {order.bitrix_deal_id:<10} {'NO STAGE':<25} {'N/A':<25} {'SKIPPED':<10}")
                    skipped_count += 1
                    continue
                
                # Remove C1: prefix
                new_status = bitrix_stage.replace("C1:", "") if bitrix_stage.startswith("C1:") else bitrix_stage
                
                # Only update if status changed
                if order.status != new_status:
                    await db.execute(
                        update(models.Order)
                        .where(models.Order.order_id == order.order_id)
                        .values(status=new_status)
                    )
                    await db.commit()
                    
                    print(f"{order.order_id:<10} {order.status:<20} {order.bitrix_deal_id:<10} {bitrix_stage:<25} {new_status:<25} {'UPDATED':<10}")
                    updated_count += 1
                else:
                    print(f"{order.order_id:<10} {order.status:<20} {order.bitrix_deal_id:<10} {bitrix_stage:<25} {new_status:<25} {'NO CHANGE':<10}")
                    skipped_count += 1
                    
            except Exception as e:
                print(f"{order.order_id:<10} {order.status:<20} {order.bitrix_deal_id or 'N/A':<10} {'ERROR':<25} {'N/A':<25} {'ERROR':<10}")
                print(f"  Error: {str(e)[:50]}")
                error_count += 1
        
        print("\n" + "=" * 100)
        print("SUMMARY")
        print("=" * 100)
        print(f"Total orders processed: {len(orders)}")
        print(f"✓ Updated: {updated_count}")
        print(f"○ Skipped (no change or no stage): {skipped_count}")
        print(f"✗ Errors: {error_count}")
        print("\n" + "=" * 100)

if __name__ == "__main__":
    asyncio.run(update_statuses())


