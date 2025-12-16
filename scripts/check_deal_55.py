"""Check if Bitrix deal 55 was updated"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.bitrix.client import bitrix_client

async def check_deal():
    if not bitrix_client.is_configured():
        print("Bitrix not configured")
        return
    
    deal = await bitrix_client.get_deal(55)
    if deal:
        print(f"Deal 55 found:")
        print(f"  Title: {deal.get('TITLE', 'N/A')}")
        print(f"  Opportunity (Price): {deal.get('OPPORTUNITY', 'N/A')}")
        print(f"  Comments (Quantity): {deal.get('COMMENTS', 'N/A')}")
        print(f"  Stage: {deal.get('STAGE_ID', 'N/A')}")
        print(f"  Category: {deal.get('CATEGORY_ID', 'N/A')}")
    else:
        print("Deal 55 not found")

if __name__ == "__main__":
    asyncio.run(check_deal())









