"""Check if worker task is actually running in app state"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.main import app

async def check():
    print("Checking worker task in app state...")
    
    if hasattr(app.state, 'bitrix_worker_task'):
        task = app.state.bitrix_worker_task
        print(f"✓ Worker task exists: {task}")
        print(f"  Task done: {task.done()}")
        print(f"  Task cancelled: {task.cancelled()}")
        
        if task.done():
            print("  ⚠️  Task is done - worker may have exited")
            try:
                result = await task
                print(f"  Task result: {result}")
            except Exception as e:
                print(f"  Task exception: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("  ✓ Task is still running")
    else:
        print("✗ No worker task in app state")
    
    # Also check worker object directly
    from backend.bitrix.worker import bitrix_worker
    print(f"\nWorker object status:")
    print(f"  Running: {bitrix_worker.running}")
    print(f"  Batch size: {bitrix_worker.batch_size}")
    print(f"  Poll interval: {bitrix_worker.poll_interval}")

if __name__ == "__main__":
    asyncio.run(check())









