"""Check if deal stages are syncing from Bitrix to database"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from sqlalchemy import select

async def check_orders():
    """Check order statuses and their Bitrix deal stages"""
    async with AsyncSessionLocal() as db:
        # Get orders with Bitrix deals
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id)
            .limit(10)
        )
        orders = result.scalars().all()
        
        print("=" * 100)
        print(f"ORDER STATUS vs BITRIX DEAL STAGE CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)
        print(f"\n{'Order ID':<10} {'DB Status':<15} {'Deal ID':<10} {'Bitrix Stage':<20} {'Match':<10}")
        print("-" * 100)
        
        for order in orders:
            # Get deal from Bitrix
            deal_data = None
            bitrix_stage = "N/A"
            try:
                deal_data = await bitrix_client.get_deal(order.bitrix_deal_id)
                if deal_data:
                    bitrix_stage = deal_data.get("STAGE_ID") or deal_data.get("stage_id", "N/A")
            except:
                bitrix_stage = "Error"
            
            match = "✓" if (order.status == "pending" and bitrix_stage in ["C1:NEW", "NEW"]) or \
                          (order.status == "processing" and bitrix_stage in ["C1:EXECUTING", "EXECUTING"]) or \
                          (order.status == "completed" and bitrix_stage in ["C1:WON", "WON"]) or \
                          (order.status == "cancelled" and bitrix_stage in ["C1:LOSE", "LOSE"]) else "✗"
            
            print(f"{order.order_id:<10} {order.status:<15} {order.bitrix_deal_id or 'N/A':<10} {bitrix_stage:<20} {match:<10}")
        
        print("\n" + "=" * 100)
        return orders

async def main():
    """Main function to check before and after"""
    print("\n" + "=" * 100)
    print("BEFORE CHECK - Current Status")
    print("=" * 100)
    orders_before = await check_orders()
    
    # Store initial statuses
    initial_statuses = {order.order_id: order.status for order in orders_before}
    
    print("\n" + "=" * 100)
    print("WAITING 3 MINUTES FOR SYNC TO RUN...")
    print("=" * 100)
    print("(The sync scheduler runs every 5 minutes, so we'll check after 3 minutes)")
    print("Please change some deal stages in Bitrix now, then we'll check again.\n")
    
    await asyncio.sleep(180)  # Wait 3 minutes
    
    print("\n" + "=" * 100)
    print("AFTER CHECK - Status After Sync")
    print("=" * 100)
    orders_after = await check_orders()
    
    # Compare statuses
    print("\n" + "=" * 100)
    print("STATUS CHANGES DETECTED:")
    print("=" * 100)
    changes_found = False
    for order in orders_after:
        initial_status = initial_statuses.get(order.order_id)
        if initial_status != order.status:
            changes_found = True
            print(f"Order {order.order_id}: {initial_status} → {order.status}")
    
    if not changes_found:
        print("No status changes detected in the checked orders.")
        print("(This could mean stages weren't changed, or sync hasn't run yet)")

if __name__ == "__main__":
    asyncio.run(main())


