"""Check if order 38 quantity update was synced to Bitrix"""
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
        # Get order 38
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 38)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("Order 38 not found!")
            return
        
        print("=" * 60)
        print("Order 38 - Quantity Update Check")
        print("=" * 60)
        
        print(f"\nDatabase Order 38:")
        print(f"  Quantity: {order.quantity}")
        print(f"  Total Price: {order.total_price}")
        print(f"  Status: {order.status}")
        print(f"  Service: {order.service_id}")
        print(f"  Updated: {order.updated_at}")
        print(f"  Bitrix Deal ID: {order.bitrix_deal_id}")
        
        if order.bitrix_deal_id:
            # Get deal from Bitrix
            deal = await bitrix_client.get_deal(order.bitrix_deal_id)
            if deal:
                print(f"\nBitrix Deal {order.bitrix_deal_id}:")
                print(f"  Title: {deal.get('TITLE', 'N/A')}")
                print(f"  Opportunity (Price): {deal.get('OPPORTUNITY', 'N/A')}")
                print(f"  Comments: {deal.get('COMMENTS', 'N/A')[:200]}")
                print(f"  Modified: {deal.get('DATE_MODIFY', 'N/A')}")
                
                # Check if quantity is in comments
                comments = deal.get('COMMENTS', '')
                if 'Quantity:' in comments:
                    # Extract quantity from comments
                    import re
                    qty_match = re.search(r'Quantity:\s*(\d+)', comments)
                    if qty_match:
                        bitrix_qty = int(qty_match.group(1))
                        print(f"\n  Quantity in Bitrix: {bitrix_qty}")
                        
                        if bitrix_qty == order.quantity:
                            print(f"\n✓ Quantity matches! ({order.quantity})")
                        else:
                            print(f"\n⚠️  Quantity mismatch!")
                            print(f"   Database: {order.quantity}")
                            print(f"   Bitrix: {bitrix_qty}")
                            print(f"   Difference: {order.quantity - bitrix_qty}")
                else:
                    print(f"\n⚠️  Quantity not found in Bitrix comments")
                    print(f"   Database quantity: {order.quantity}")
                
                # Check price match
                deal_price = float(deal.get('OPPORTUNITY', 0) or 0)
                order_price = float(order.total_price or 0)
                
                if abs(deal_price - order_price) < 0.01:
                    print(f"\n✓ Price matches! ({order_price})")
                else:
                    print(f"\n⚠️  Price mismatch!")
                    print(f"   Database: {order_price}")
                    print(f"   Bitrix: {deal_price}")
                    print(f"   Difference: {order_price - deal_price}")
                
                # Check if update is needed
                needs_update = False
                if 'Quantity:' in comments:
                    qty_match = re.search(r'Quantity:\s*(\d+)', comments)
                    if qty_match:
                        bitrix_qty = int(qty_match.group(1))
                        if bitrix_qty != order.quantity:
                            needs_update = True
                else:
                    needs_update = True
                
                if abs(deal_price - order_price) >= 0.01:
                    needs_update = True
                
                if needs_update:
                    print(f"\n⚠️  Update needed - queueing deal update...")
                    from backend.bitrix.sync_service import bitrix_sync_service
                    await bitrix_sync_service.queue_deal_update(db, order.order_id)
                    print(f"   ✓ Deal update queued to Redis")
                else:
                    print(f"\n✓ Deal is up to date")
            else:
                print(f"\n❌ Deal {order.bitrix_deal_id} not found in Bitrix")
        else:
            print(f"\n⚠️  No Bitrix deal ID - deal not created yet")

if __name__ == "__main__":
    asyncio.run(main())









