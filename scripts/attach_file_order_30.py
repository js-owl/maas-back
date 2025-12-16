"""Attach file to order 30's Bitrix deal"""
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
        # Get order 30
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 30)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("Order 30 not found!")
            return
        
        if not order.bitrix_deal_id:
            print("Order 30 has no Bitrix deal ID!")
            return
        
        deal_id = order.bitrix_deal_id
        print(f"Order 30 has Bitrix deal ID: {deal_id}")
        
        # Try to find a demo file or use a default file
        demo_file_path = Path("uploads/3d_models/demo_printing_default.stp")
        if not demo_file_path.exists():
            # Try to find any .stp or .stl file
            uploads_dir = Path("uploads/3d_models")
            if uploads_dir.exists():
                files = list(uploads_dir.glob("*.stp")) + list(uploads_dir.glob("*.stl"))
                if files:
                    demo_file_path = files[0]
                    print(f"Using file: {demo_file_path}")
                else:
                    print("No files found in uploads/3d_models/")
                    return
            else:
                print("Uploads directory not found")
                return
        else:
            print(f"Using demo file: {demo_file_path}")
        
        # Attach file
        filename = demo_file_path.name
        print(f"Attaching file: {demo_file_path} to deal {deal_id}")
        print(f"File field code: {bitrix_client.deal_file_field_code}")
        
        success = await bitrix_client.attach_file_to_deal(
            deal_id, 
            str(demo_file_path), 
            filename
        )
        
        if success:
            print(f"✓ File attached successfully!")
        else:
            print(f"✗ Failed to attach file")
        
        # Verify attachment
        print(f"\nVerifying attachment...")
        deal = await bitrix_client.get_deal(deal_id)
        if deal:
            file_field_code = bitrix_client.deal_file_field_code
            file_value = deal.get(file_field_code)
            if file_value:
                print(f"✓ File is attached to deal (field '{file_field_code}': {file_value})")
            else:
                print(f"✗ File is NOT attached (field '{file_field_code}' is empty)")

if __name__ == "__main__":
    asyncio.run(main())
