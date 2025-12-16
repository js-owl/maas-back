"""Check deal 15 details"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.client import bitrix_client

async def main():
    deal_id = 15
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
        print(f"  Type: {type(file_value)}")
        
        if file_value:
            print(f"✓ File is attached!")
            if isinstance(file_value, list):
                print(f"  File IDs: {file_value}")
            else:
                print(f"  File ID: {file_value}")
        else:
            print(f"✗ File is NOT attached (field is empty or None)")
            
        # List all UF_ fields
        print(f"\nAll UF_ fields:")
        for key in sorted(deal.keys()):
            if key.startswith('UF_'):
                print(f"  {key}: {deal[key]} (type: {type(deal[key])})")

if __name__ == "__main__":
    asyncio.run(main())









