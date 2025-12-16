"""Check which orders have files and which have files attached in Bitrix"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        # Get all orders with Bitrix deals
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        print(f"Checking {len(orders)} orders with Bitrix deals...\n")
        
        orders_with_files = 0
        orders_with_attached_files = 0
        orders_without_files = 0
        
        for order in orders:
            has_file = order.file_id is not None
            has_attached = False
            
            if has_file:
                orders_with_files += 1
                # Check if file is attached in Bitrix
                deal = await bitrix_client.get_deal(order.bitrix_deal_id)
                if deal:
                    file_field_code = bitrix_client.deal_file_field_code
                    file_value = deal.get(file_field_code)
                    if file_value:
                        has_attached = True
                        orders_with_attached_files += 1
                        print(f"✓ Order {order.order_id} (Deal {order.bitrix_deal_id}): File attached")
                    else:
                        print(f"✗ Order {order.order_id} (Deal {order.bitrix_deal_id}): Has file_id={order.file_id} but NOT attached in Bitrix")
            else:
                orders_without_files += 1
                print(f"- Order {order.order_id} (Deal {order.bitrix_deal_id}): No file_id")
        
        print(f"\nSummary:")
        print(f"  Total orders with deals: {len(orders)}")
        print(f"  Orders with file_id: {orders_with_files}")
        print(f"  Orders with files attached in Bitrix: {orders_with_attached_files}")
        print(f"  Orders without files: {orders_without_files}")
        print(f"  Orders with files but not attached: {orders_with_files - orders_with_attached_files}")

if __name__ == "__main__":
    asyncio.run(main())









