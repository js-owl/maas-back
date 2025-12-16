"""Force process order 39 deal creation"""
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
        # Get order 39
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 39)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("Order 39 not found!")
            return
        
        print(f"Order 39:")
        print(f"  Status: {order.status}")
        print(f"  User ID: {order.user_id}")
        print(f"  Bitrix Deal ID: {order.bitrix_deal_id or 'NOT SET'}")
        
        if order.bitrix_deal_id:
            print(f"\n✓ Order 39 already has Bitrix deal {order.bitrix_deal_id}")
            return
        
        # Manually process deal creation
        print(f"\nProcessing deal creation for order 39...")
        
        payload = {
            "order_id": order.order_id,
            "user_id": order.user_id,
            "file_id": order.file_id,
            "document_ids": order.document_ids or [],
            "order_data": {
                "service_id": order.service_id,
                "quantity": order.quantity,
                "total_price": order.total_price,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None
            }
        }
        
        success = await bitrix_worker._process_deal_operation(
            db,
            order.order_id,
            "create",
            payload
        )
        
        if success:
            print(f"✓ Deal creation successful!")
            # Refresh order
            await db.refresh(order)
            print(f"  New Bitrix Deal ID: {order.bitrix_deal_id}")
        else:
            print(f"❌ Deal creation failed!")

if __name__ == "__main__":
    asyncio.run(main())









