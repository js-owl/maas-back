"""Cleanup duplicate deals for order 39"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend.bitrix.cleanup_service import bitrix_cleanup_service

async def main():
    async with AsyncSessionLocal() as db:
        print("Cleaning up duplicate deals for order 39...\n")
        
        result = await bitrix_cleanup_service.cleanup_duplicate_deals_for_order(db, 39)
        
        print(f"Results:")
        print(f"  Order ID: {result['order_id']}")
        print(f"  Deals found: {result['deals_found']}")
        print(f"  Deals deleted: {result['deals_deleted']}")
        print(f"  Deal kept: {result['deal_kept']}")
        
        if result['errors']:
            print(f"\nErrors:")
            for error in result['errors']:
                print(f"  - {error}")

if __name__ == "__main__":
    asyncio.run(main())









