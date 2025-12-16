"""Check Redis queue status"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.queue_service import bitrix_queue_service

async def main():
    # Check operations stream
    ops_info = await bitrix_queue_service.get_stream_info(bitrix_queue_service.operations_stream)
    print(f"Operations stream:")
    print(f"  Length: {ops_info.get('length', 0)}")
    print(f"  Groups: {ops_info.get('groups', 0)}")
    print(f"  Last ID: {ops_info.get('last_id', '0-0')}")
    
    # Check webhooks stream
    webhooks_info = await bitrix_queue_service.get_stream_info(bitrix_queue_service.webhooks_stream)
    print(f"\nWebhooks stream:")
    print(f"  Length: {webhooks_info.get('length', 0)}")
    print(f"  Groups: {webhooks_info.get('groups', 0)}")
    print(f"  Last ID: {webhooks_info.get('last_id', '0-0')}")

if __name__ == "__main__":
    asyncio.run(main())
