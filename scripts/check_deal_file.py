"""Check if file is attached to deal"""
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
        print(f"Checking deal {deal_id} in Bitrix...")
        
        # Get deal from Bitrix
        deal = await bitrix_client.get_deal(deal_id)
        if deal:
            print(f"\nDeal details:")
            print(f"  Title: {deal.get('TITLE', 'N/A')}")
            print(f"  Category ID: {deal.get('CATEGORY_ID', 'N/A')}")
            print(f"  Stage ID: {deal.get('STAGE_ID', 'N/A')}")
            
            # Check file field
            file_field_code = bitrix_client.deal_file_field_code
            file_value = deal.get(file_field_code)
            print(f"\nFile field '{file_field_code}': {file_value}")
            
            if file_value:
                print(f"✓ File is attached!")
            else:
                print(f"✗ File is NOT attached (field is empty or None)")
                
            # List all fields to see what's available
            print(f"\nAll deal fields (keys):")
            for key in sorted(deal.keys()):
                if key.startswith('UF_') or 'FILE' in key.upper():
                    print(f"  {key}: {deal[key]}")
        else:
            print("Failed to get deal from Bitrix")

if __name__ == "__main__":
    asyncio.run(main())









