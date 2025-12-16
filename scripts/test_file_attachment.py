"""Test file attachment to deal and check response"""
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
        
        if not order or not order.bitrix_deal_id:
            print("Order 38 not found or has no Bitrix deal ID!")
            return
        
        deal_id = order.bitrix_deal_id
        print(f"Testing file attachment for deal {deal_id}")
        
        # Get file
        if order.file_id:
            from backend.files.service import get_file_by_id
            file_record = await get_file_by_id(db, order.file_id)
            if file_record and file_record.file_path:
                file_path = Path(file_record.file_path)
                if file_path.exists():
                    print(f"File found: {file_path}")
                    print(f"File field code: {bitrix_client.deal_file_field_code}")
                    
                    # Try to attach
                    success = await bitrix_client.attach_file_to_deal(
                        deal_id, 
                        str(file_path), 
                        file_record.filename
                    )
                    print(f"Attachment result: {success}")
                else:
                    print(f"File not found at path: {file_path}")
            else:
                print("File record not found")
        else:
            print("Order has no file_id")

if __name__ == "__main__":
    asyncio.run(main())









