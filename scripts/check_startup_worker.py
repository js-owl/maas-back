"""Check if worker task is created on startup"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Simulate startup
from backend.main import app

async def check():
    # Check if worker task exists in app state
    if hasattr(app.state, 'bitrix_worker_task'):
        task = app.state.bitrix_worker_task
        print(f"Worker task exists: {task}")
        print(f"Task done: {task.done()}")
        if task.done():
            try:
                result = await task
                print(f"Task result: {result}")
            except Exception as e:
                print(f"Task exception: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"Task is running")
    else:
        print("No worker task in app state")

if __name__ == "__main__":
    asyncio.run(check())









