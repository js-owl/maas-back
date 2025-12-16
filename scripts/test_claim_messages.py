"""Test claiming pending messages"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.queue_service import bitrix_queue_service

async def main():
    print("Testing claim pending messages...")
    
    # Claim pending messages
    claimed = await bitrix_queue_service.claim_pending_messages(
        bitrix_queue_service.operations_stream,
        min_idle_time_ms=60000,  # 1 minute
        count=10
    )
    
    print(f"\nClaimed {len(claimed)} messages:")
    for msg in claimed:
        print(f"  Message ID: {msg.get('id')}")
        print(f"    Entity: {msg.get('entity_type')} {msg.get('entity_id')}")
        print(f"    Operation: {msg.get('operation')}")
        print(f"    Retry count: {msg.get('retry_count', '0')}")
    
    if claimed:
        print(f"\n✓ Successfully claimed {len(claimed)} messages")
        print(f"  These should now be processed by the worker")
    else:
        print(f"\n⚠️  No messages were claimed")
        print(f"  This could mean:")
        print(f"    - All messages are too recent (< 60s idle)")
        print(f"    - All messages are already processed")
        print(f"    - Claim logic has an issue")

if __name__ == "__main__":
    asyncio.run(main())









