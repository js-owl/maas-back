"""Force update order 38 deal in Bitrix"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend.bitrix.worker import bitrix_worker
from backend import models
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        # Get order 38
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 38)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("Order 38 not found!")
            return
        
        print(f"Order 38:")
        print(f"  Quantity: {order.quantity}")
        print(f"  Total Price: {order.total_price}")
        print(f"  Bitrix Deal ID: {order.bitrix_deal_id}")
        
        if not order.bitrix_deal_id:
            print("No Bitrix deal ID!")
            return
        
        # Manually process deal update
        print(f"\nProcessing deal update for order 38...")
        
        payload = {
            "order_id": order.order_id,
            "user_id": order.user_id
        }
        
        success = await bitrix_worker._process_deal_operation(
            db,
            order.order_id,
            "update",
            payload
        )
        
        if success:
            print(f"✓ Deal update successful!")
            
            # Check updated deal
            from backend.bitrix.client import bitrix_client
            deal = await bitrix_client.get_deal(order.bitrix_deal_id)
            if deal:
                comments = deal.get('COMMENTS', '')
                import re
                qty_match = re.search(r'Quantity:\s*(\d+)', comments)
                if qty_match:
                    bitrix_qty = int(qty_match.group(1))
                    print(f"  Updated quantity in Bitrix: {bitrix_qty}")
                    if bitrix_qty == order.quantity:
                        print(f"  ✓ Quantity matches database!")
                    else:
                        print(f"  ⚠️  Still doesn't match (DB: {order.quantity}, Bitrix: {bitrix_qty})")
        else:
            print(f"❌ Deal update failed!")

if __name__ == "__main__":
    asyncio.run(main())









