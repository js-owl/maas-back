"""Test worker directly"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.bitrix.worker import bitrix_worker
from backend.utils.logging import get_logger

logger = get_logger(__name__)

async def test_worker():
    print("=" * 60)
    print("Testing Worker Directly")
    print("=" * 60)
    
    print(f"Worker object: {bitrix_worker}")
    print(f"Worker running before: {bitrix_worker.running}")
    
    try:
        print("Calling process_messages()...")
        # Run for a short time to see if it starts
        task = asyncio.create_task(bitrix_worker.process_messages())
        await asyncio.sleep(3)
        print(f"Worker running after 3 seconds: {bitrix_worker.running}")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            print("Task cancelled successfully")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_worker())
