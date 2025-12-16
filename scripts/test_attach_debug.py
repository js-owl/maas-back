"""Debug file attachment for deal 15"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.client import bitrix_client

async def main():
    deal_id = 15
    file_path = "uploads/3d_models/demo_printing_default.stp"
    filename = "demo_printing_default.stp"
    
    print(f"Uploading file: {file_path}")
    file_id = await bitrix_client.upload_file_to_disk(file_path, filename)
    print(f"File ID returned: {file_id} (type: {type(file_id)})")
    
    if file_id:
        # Try updating deal with detailed logging
        print(f"\nUpdating deal {deal_id} with file ID: {file_id}")
        
        # Try single value
        payload1 = {
            "id": deal_id,
            "fields": {
                bitrix_client.deal_file_field_code: file_id
            }
        }
        print(f"Payload 1 (single value): {payload1}")
        resp1 = await bitrix_client._post("crm.deal.update", payload1)
        print(f"Response 1: {resp1}")
        
        if not (resp1 and resp1.get("result")):
            # Try array format
            payload2 = {
                "id": deal_id,
                "fields": {
                    bitrix_client.deal_file_field_code: [file_id]
                }
            }
            print(f"\nPayload 2 (array): {payload2}")
            resp2 = await bitrix_client._post("crm.deal.update", payload2)
            print(f"Response 2: {resp2}")
        
        # Verify
        print(f"\nVerifying...")
        deal = await bitrix_client.get_deal(deal_id)
        if deal:
            file_value = deal.get(bitrix_client.deal_file_field_code)
            print(f"File field value: {file_value} (type: {type(file_value)})")

if __name__ == "__main__":
    asyncio.run(main())









