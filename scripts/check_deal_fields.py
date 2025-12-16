"""Check deal fields to see if file field exists"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.client import bitrix_client

async def main():
    print("Checking deal fields in Bitrix...")
    
    # Get deal fields
    fields = await bitrix_client.get_deal_fields()
    if fields:
        print(f"\nDeal fields found:")
        file_field_code = bitrix_client.deal_file_field_code
        print(f"\nLooking for field: {file_field_code}")
        
        # Search for file-related fields
        file_fields = []
        for field_code, field_info in fields.items():
            if isinstance(field_info, dict):
                field_type = field_info.get('TYPE', '')
                if 'FILE' in field_type.upper() or 'file' in field_code.lower():
                    file_fields.append((field_code, field_info))
                    print(f"\n  {field_code}:")
                    print(f"    Type: {field_info.get('TYPE', 'N/A')}")
                    print(f"    Title: {field_info.get('TITLE', 'N/A')}")
                    print(f"    List: {field_info.get('LIST', 'N/A')}")
        
        # Check if our field exists
        if file_field_code in fields:
            print(f"\n✓ Field '{file_field_code}' exists!")
            field_info = fields[file_field_code]
            print(f"  Type: {field_info.get('TYPE', 'N/A')}")
            print(f"  Title: {field_info.get('TITLE', 'N/A')}")
            print(f"  List: {field_info.get('LIST', 'N/A')}")
        else:
            print(f"\n✗ Field '{file_field_code}' does NOT exist!")
            print(f"\nAvailable file-related fields:")
            for field_code, field_info in file_fields:
                print(f"  - {field_code}")
    else:
        print("Failed to get deal fields")

if __name__ == "__main__":
    asyncio.run(main())









