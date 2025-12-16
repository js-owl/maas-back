"""Recheck stage sync after Bitrix updates"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager
from sqlalchemy import select

async def check():
    """Check all orders and compare with Bitrix"""
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
        
        print("=" * 120)
        print(f"STAGE SYNC RECHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 120)
        print(f"\nChecking {len(orders)} orders with Bitrix deals...\n")
        
        print(f"{'Order':<8} {'DB Status':<15} {'Deal ID':<10} {'Bitrix Stage':<25} {'Mapped Status':<15} {'Match':<8} {'Updated':<20}")
        print("-" * 120)
        
        mismatches = []
        matches = []
        recently_updated = []
        
        for order in orders:
            try:
                # Get deal from Bitrix
                deal_data = await bitrix_client.get_deal(order.bitrix_deal_id)
                if not deal_data:
                    print(f"{order.order_id:<8} {order.status:<15} {order.bitrix_deal_id:<10} {'NOT FOUND':<25} {'N/A':<15} {'?':<8} {str(order.updated_at)[:19]}")
                    continue
                
                bitrix_stage = deal_data.get("STAGE_ID") or deal_data.get("stage_id", "N/A")
                stage_name = deal_data.get("STAGE_NAME") or deal_data.get("stageName", "N/A")
                
                # Map stage to status
                mapped_status = None
                if funnel_manager.is_initialized():
                    mapped_status = funnel_manager.get_status_for_stage_id(bitrix_stage)
                
                # Check if status matches
                if mapped_status:
                    match = "✓" if mapped_status == order.status else "✗"
                    if mapped_status == order.status:
                        matches.append(order.order_id)
                    else:
                        mismatches.append({
                            "order_id": order.order_id,
                            "db_status": order.status,
                            "bitrix_stage": bitrix_stage,
                            "mapped_status": mapped_status
                        })
                else:
                    match = "?"
                
                # Check if recently updated (last 10 minutes)
                ten_min_ago = datetime.now() - timedelta(minutes=10)
                is_recent = order.updated_at.replace(tzinfo=None) >= ten_min_ago.replace(tzinfo=None) if order.updated_at else False
                updated_str = str(order.updated_at)[:19] if order.updated_at else "N/A"
                if is_recent:
                    recently_updated.append(order.order_id)
                    updated_str = f"**{updated_str}**"
                
                print(f"{order.order_id:<8} {order.status:<15} {order.bitrix_deal_id:<10} {bitrix_stage:<25} {mapped_status or 'N/A':<15} {match:<8} {updated_str}")
                
            except Exception as e:
                print(f"{order.order_id:<8} {order.status:<15} {order.bitrix_deal_id:<10} {'ERROR':<25} {'N/A':<15} {'?':<8} {str(order.updated_at)[:19]}")
        
        print("\n" + "=" * 120)
        print("SUMMARY")
        print("=" * 120)
        print(f"\nTotal orders checked: {len(orders)}")
        print(f"✓ Matches: {len(matches)}")
        print(f"✗ Mismatches: {len(mismatches)}")
        print(f"🔄 Recently updated (last 10 min): {len(recently_updated)}")
        
        if recently_updated:
            print(f"\nRecently updated orders: {recently_updated}")
        
        if mismatches:
            print(f"\n⚠ MISMATCHES DETECTED (DB status doesn't match Bitrix stage):")
            for mm in mismatches:
                print(f"  Order {mm['order_id']}: DB has '{mm['db_status']}', but Bitrix stage '{mm['bitrix_stage']}' maps to '{mm['mapped_status']}'")
                print(f"    → This order needs to be synced!")
        
        print("\n" + "=" * 120)
        print("FUNNEL MAPPING REFERENCE")
        print("=" * 120)
        if funnel_manager.is_initialized():
            status_mapping = funnel_manager.get_status_mapping()
            print("\nBitrix Stage → Order Status:")
            for stage, status in status_mapping.items():
                print(f"  {stage} → {status}")

if __name__ == "__main__":
    asyncio.run(check())


