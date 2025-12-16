"""Manually queue order 38 for Bitrix sync"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend.bitrix.sync_service import bitrix_sync_service

async def main():
    async with AsyncSessionLocal() as db:
        print("Manually queuing order 38 for Bitrix sync...")
        try:
            await bitrix_sync_service.queue_deal_creation(db, 38, 1, 1, [])
            print("Order 38 queued successfully!")
        except Exception as e:
            print(f"Error queuing order 38: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())









