"""Check recent Redis messages for order 39"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import redis.asyncio as redis
from backend.core.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_STREAM_PREFIX
import json

async def main():
    redis_client = await redis.Redis(
        host=REDIS_HOST,
        port=int(REDIS_PORT),
        db=int(REDIS_DB),
        decode_responses=True
    )
    
    operations_stream = f"{REDIS_STREAM_PREFIX}operations"
    
    # Get last 20 messages
    messages = await redis_client.xrevrange(operations_stream, count=20)
    
    print(f"Last 20 messages in {operations_stream}:")
    print("=" * 60)
    
    for msg_id, fields in messages:
        try:
            data = json.loads(fields.get('data', '{}'))
            entity_type = fields.get('entity_type', 'unknown')
            entity_id = fields.get('entity_id', 'unknown')
            operation = fields.get('operation', 'unknown')
            
            if entity_type == 'deal' and (entity_id == '39' or '39' in str(data)):
                print(f"\n🔍 FOUND ORDER 39 MESSAGE:")
                print(f"  Message ID: {msg_id}")
                print(f"  Entity Type: {entity_type}")
                print(f"  Entity ID: {entity_id}")
                print(f"  Operation: {operation}")
                print(f"  Data: {json.dumps(data, indent=2)[:200]}")
            elif entity_type == 'deal':
                print(f"\n  Deal {entity_id} - {operation}")
        except:
            print(f"\n  Message {msg_id}: {fields}")
    
    # Check pending messages
    consumer_group = "bitrix_worker"
    try:
        pending = await redis_client.xpending_range(
            operations_stream,
            consumer_group,
            min="-",
            max="+",
            count=100
        )
        if pending:
            print(f"\n\nPending messages: {len(pending)}")
            for msg in pending[:10]:
                print(f"  - {msg}")
    except Exception as e:
        print(f"\nNo pending messages or error: {e}")

if __name__ == "__main__":
    asyncio.run(main())









