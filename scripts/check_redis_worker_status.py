"""Check Redis queue and worker status"""
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
    consumer_group = "bitrix_worker"
    consumer_name = "worker_1"
    
    print("=" * 60)
    print("Redis Queue and Worker Status")
    print("=" * 60)
    
    # Check stream length
    stream_length = await redis_client.xlen(operations_stream)
    print(f"\nStream: {operations_stream}")
    print(f"  Total messages: {stream_length}")
    
    # Check consumer group info
    try:
        groups = await redis_client.xinfo_groups(operations_stream)
        print(f"\nConsumer Groups:")
        for group in groups:
            print(f"  Group: {group['name']}")
            print(f"    Consumers: {group['consumers']}")
            print(f"    Pending: {group['pending']}")
            print(f"    Last delivered ID: {group['last-delivered-id']}")
    except Exception as e:
        print(f"\n⚠️  Error getting consumer groups: {e}")
        print(f"   Consumer group may not exist")
    
    # Check pending messages
    try:
        pending = await redis_client.xpending_range(
            operations_stream,
            consumer_group,
            min="-",
            max="+",
            count=20
        )
        print(f"\nPending Messages: {len(pending)}")
        if pending:
            for msg in pending[:10]:
                print(f"  Message ID: {msg['message_id']}")
                print(f"    Consumer: {msg['consumer']}")
                print(f"    Idle time (ms): {msg['time_since_delivered']}")
                print(f"    Delivery count: {msg['times_delivered']}")
        else:
            print("  No pending messages")
    except Exception as e:
        print(f"\n⚠️  Error getting pending messages: {e}")
        print(f"   This might mean consumer group doesn't exist")
    
    # Check consumer info
    try:
        consumers = await redis_client.xinfo_consumers(operations_stream, consumer_group)
        print(f"\nConsumers in group '{consumer_group}': {len(consumers)}")
        for consumer in consumers:
            print(f"  Consumer: {consumer['name']}")
            print(f"    Pending: {consumer['pending']}")
            print(f"    Idle time (ms): {consumer['idle']}")
    except Exception as e:
        print(f"\n⚠️  Error getting consumer info: {e}")
    
    # Get recent messages
    print(f"\nRecent Messages (last 10):")
    try:
        messages = await redis_client.xrevrange(operations_stream, count=10)
        for msg_id, fields in messages:
            entity_type = fields.get('entity_type', 'unknown')
            entity_id = fields.get('entity_id', 'unknown')
            operation = fields.get('operation', 'unknown')
            print(f"  {msg_id}: {entity_type} {entity_id} - {operation}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Try to read messages as the consumer would
    print(f"\nAttempting to read messages as consumer '{consumer_name}':")
    try:
        # First ensure consumer group exists
        try:
            await redis_client.xgroup_create(
                operations_stream,
                consumer_group,
                id="0",
                mkstream=True
            )
            print(f"  ✓ Created consumer group '{consumer_group}'")
        except Exception as e:
            if "BUSYGROUP" in str(e):
                print(f"  ✓ Consumer group '{consumer_group}' already exists")
            else:
                print(f"  ⚠️  Error creating group: {e}")
        
        # Try to read new messages
        messages = await redis_client.xreadgroup(
            groupname=consumer_group,
            consumername=consumer_name,
            streams={operations_stream: ">"},
            count=5,
            block=1000
        )
        
        if messages:
            print(f"  Found {len(messages[0][1])} new messages")
            for msg_id, fields in messages[0][1]:
                print(f"    {msg_id}: {fields.get('entity_type')} {fields.get('entity_id')} - {fields.get('operation')}")
        else:
            print(f"  No new messages (this is normal if all are processed)")
        
        # Try to read pending messages
        pending_messages = await redis_client.xreadgroup(
            groupname=consumer_group,
            consumername=consumer_name,
            streams={operations_stream: "0"},
            count=5
        )
        
        if pending_messages:
            print(f"  Found {len(pending_messages[0][1])} unprocessed messages from start")
        else:
            print(f"  No unprocessed messages from start")
            
    except Exception as e:
        print(f"  ⚠️  Error reading messages: {e}")
        import traceback
        traceback.print_exc()
    
    await redis_client.aclose()

if __name__ == "__main__":
    asyncio.run(main())









