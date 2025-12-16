"""Manually trigger Bitrix deal sync"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend.bitrix.deal_sync_service import deal_sync_service
from backend.utils.logging import get_logger

logger = get_logger(__name__)


async def run_sync():
    """Run deal sync manually"""
    try:
        async with AsyncSessionLocal() as db:
            logger.info("Starting manual deal sync...")
            stats = await deal_sync_service.sync_all_orders(db)
            logger.info(f"Sync completed: {stats}")
            print("\n" + "=" * 60)
            print("SYNC RESULTS:")
            print("=" * 60)
            for key, value in stats.items():
                print(f"  {key}: {value}")
            print("=" * 60)
    except Exception as e:
        logger.error(f"Error running sync: {e}", exc_info=True)
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_sync())


