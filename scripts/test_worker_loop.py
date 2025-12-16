"""Test if worker loop runs"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.worker import bitrix_worker
from backend.utils.logging import get_logger

logger = get_logger(__name__)

async def test_worker():
    print("Testing worker loop...")
    print(f"Worker running before: {bitrix_worker.running}")
    
    # Start worker in background
    task = asyncio.create_task(bitrix_worker.process_messages())
    
    # Wait a bit
    await asyncio.sleep(3)
    
    print(f"Worker running after 3s: {bitrix_worker.running}")
    print(f"Task done: {task.done()}")
    if task.done():
        try:
            result = await task
            print(f"Task result: {result}")
        except Exception as e:
            print(f"Task exception: {e}")
            import traceback
            traceback.print_exc()
    
    # Stop worker
    bitrix_worker.running = False
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    asyncio.run(test_worker())









