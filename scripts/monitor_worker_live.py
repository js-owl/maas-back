"""Monitor worker status in real-time"""
import asyncio
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.worker import bitrix_worker
from backend.bitrix.queue_service import bitrix_queue_service

async def monitor():
    print("Monitoring worker status...")
    print("Press Ctrl+C to stop\n")
    
    for i in range(30):  # Monitor for 30 seconds
        running = bitrix_worker.running
        print(f"[{i+1}s] Worker running: {running}", end="")
        
        if running:
            # Try to get messages
            try:
                messages = await bitrix_queue_service.get_pending_messages(
                    bitrix_queue_service.operations_stream,
                    count=1,
                    block_ms=0
                )
                print(f" | Messages available: {len(messages)}")
            except Exception as e:
                print(f" | Error: {e}")
        else:
            print(" | Worker not running!")
        
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(monitor())
    except KeyboardInterrupt:
        print("\nMonitoring stopped")









