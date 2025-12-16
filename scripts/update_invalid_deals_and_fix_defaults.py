"""Update invalid deals to LOSE and ensure database columns exist"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select, update, text

async def update_invalid_deals():
    """Update orders with invalid Bitrix deals to LOSE status"""
    invalid_deal_ids = [32, 33, 34, 35, 36, 37, 38]
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.in_(invalid_deal_ids))
        )
        orders = result.scalars().all()
        
        print("=" * 80)
        print("UPDATING INVALID DEALS TO LOSE STATUS")
        print("=" * 80)
        print(f"\nFound {len(orders)} orders with invalid deals\n")
        
        for order in orders:
            old_status = order.status
            await db.execute(
                update(models.Order)
                .where(models.Order.order_id == order.order_id)
                .values(status="LOSE")
            )
            print(f"Order {order.order_id}: {old_status} → LOSE")
        
        await db.commit()
        print(f"\n✓ Updated {len(orders)} orders to LOSE status")

async def ensure_invoice_ids_column():
    """Ensure invoice_ids column exists in orders table"""
    async with AsyncSessionLocal() as db:
        try:
            # Check if invoice_ids column exists
            result = await db.execute(text("PRAGMA table_info('orders')"))
            order_cols = {row[1] for row in result}
            
            if 'invoice_ids' not in order_cols:
                print("\n" + "=" * 80)
                print("ADDING invoice_ids COLUMN")
                print("=" * 80)
                await db.execute(text("ALTER TABLE orders ADD COLUMN invoice_ids TEXT"))
                await db.commit()
                print("✓ Added invoice_ids column to orders table")
            else:
                print("\n✓ invoice_ids column already exists")
        except Exception as e:
            print(f"\n✗ Error ensuring invoice_ids column: {e}")
            await db.rollback()

async def main():
    """Main function"""
    await ensure_invoice_ids_column()
    await update_invalid_deals()
    print("\n" + "=" * 80)
    print("ALL UPDATES COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())


