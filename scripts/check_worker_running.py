"""Check if worker is actually running and processing"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.worker import bitrix_worker
from backend.bitrix.queue_service import bitrix_queue_service

async def main():
    print("=" * 60)
    print("Worker Status Check")
    print("=" * 60)
    
    print(f"\nWorker running: {bitrix_worker.running}")
    print(f"Worker batch size: {bitrix_worker.batch_size}")
    print(f"Worker poll interval: {bitrix_worker.poll_interval}s")
    
    # Try to get messages as worker would
    print(f"\nTesting message retrieval (as worker would):")
    
    messages = await bitrix_queue_service.get_pending_messages(
        bitrix_queue_service.operations_stream,
        count=5,
        block_ms=2000
    )
    
    print(f"  Retrieved {len(messages)} messages")
    for msg in messages:
        print(f"    {msg.get('entity_type')} {msg.get('entity_id')} - {msg.get('operation')}")
    
    if messages:
        print(f"\n✓ Messages are available for processing")
        print(f"  Worker should be processing these if it's running")
    else:
        print(f"\n⚠️  No messages retrieved")
        print(f"  This could mean all messages are processed or worker isn't reading correctly")

if __name__ == "__main__":
    asyncio.run(main())









