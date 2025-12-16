"""Check order 41 and deal 65 in database"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select

async def check_order_41():
    """Check order 41 in database"""
    print("=" * 80)
    print("CHECKING ORDER 41 IN DATABASE")
    print("=" * 80)
    
    try:
        async with AsyncSessionLocal() as db:
            # Get order 41
            result = await db.execute(
                select(models.Order).where(models.Order.order_id == 41)
            )
            order = result.scalar_one_or_none()
            
            if not order:
                print("\n❌ Order 41 not found in database!")
                return
            
            print(f"\n✅ Order 41 found:")
            print(f"   Order ID: {order.order_id}")
            print(f"   Bitrix Deal ID: {order.bitrix_deal_id}")
            print(f"   Status: {order.status}")
            print(f"   Created: {order.created_at}")
            print(f"   Updated: {order.updated_at}")
            
            if order.bitrix_deal_id:
                print(f"\n📋 Deal {order.bitrix_deal_id} is associated with order 41")
                if order.bitrix_deal_id == 65:
                    print(f"   ✅ This matches deal 65!")
                else:
                    print(f"   ⚠️  Expected deal 65, but found deal {order.bitrix_deal_id}")
            else:
                print(f"\n⚠️  Order 41 has no bitrix_deal_id set")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_order_41())


