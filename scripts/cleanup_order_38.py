"""Cleanup duplicate deals for order 38"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend.bitrix.cleanup_service import bitrix_cleanup_service

async def main():
    async with AsyncSessionLocal() as db:
        print("Cleaning up duplicate deals for order 38...\n")
        
        # First, find duplicates
        duplicates = await bitrix_cleanup_service.find_duplicate_deals_for_order(38)
        
        print(f"Found {len(duplicates)} deals matching order 38:")
        for deal in duplicates:
            print(f"  Deal ID: {deal.get('ID')}, Title: {deal.get('TITLE')}, Created: {deal.get('DATE_CREATE')}")
        
        if duplicates:
            print(f"\nCleaning up...")
            result = await bitrix_cleanup_service.cleanup_duplicate_deals_for_order(db, 38)
            
            print(f"\nResults:")
            print(f"  Order ID: {result['order_id']}")
            print(f"  Deals found: {result['deals_found']}")
            print(f"  Deals deleted: {result['deals_deleted']}")
            print(f"  Deal kept: {result['deal_kept']}")
            
            if result['errors']:
                print(f"\nErrors:")
                for error in result['errors']:
                    print(f"  - {error}")
        else:
            print("No duplicate deals found.")

if __name__ == "__main__":
    asyncio.run(main())









