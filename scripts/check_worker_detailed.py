"""Detailed check of worker and Redis status"""
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
    consumer_group = "bitrix_workers"  # Note: plural, as used by worker
    
    print("=" * 60)
    print("Detailed Worker and Redis Status")
    print("=" * 60)
    
    # Stream info
    stream_length = await redis_client.xlen(operations_stream)
    print(f"\nStream: {operations_stream}")
    print(f"  Total messages: {stream_length}")
    
    # Consumer group info
    try:
        groups = await redis_client.xinfo_groups(operations_stream)
        print(f"\nConsumer Groups:")
        for group in groups:
            print(f"  Group: {group['name']}")
            print(f"    Consumers: {group['consumers']}")
            print(f"    Pending: {group['pending']}")
            print(f"    Last delivered ID: {group['last-delivered-id']}")
    except Exception as e:
        print(f"\nError: {e}")
    
    # Consumers in bitrix_workers group
    try:
        consumers = await redis_client.xinfo_consumers(operations_stream, consumer_group)
        print(f"\nConsumers in '{consumer_group}' group: {len(consumers)}")
        for consumer in consumers:
            print(f"  Consumer: {consumer['name']}")
            print(f"    Pending: {consumer['pending']}")
            print(f"    Idle time (ms): {consumer['idle']}")
    except Exception as e:
        print(f"\nError getting consumers: {e}")
    
    # Pending messages
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
            for msg in pending:
                print(f"  Message ID: {msg['message_id']}")
                print(f"    Consumer: {msg['consumer']}")
                print(f"    Idle time (ms): {msg['time_since_delivered']}")
                print(f"    Delivery count: {msg['times_delivered']}")
                
                # Get message details
                try:
                    msg_data = await redis_client.xrange(operations_stream, msg['message_id'], msg['message_id'], count=1)
                    if msg_data:
                        fields = msg_data[0][1]
                        entity_type = fields.get('entity_type', 'unknown')
                        entity_id = fields.get('entity_id', 'unknown')
                        operation = fields.get('operation', 'unknown')
                        print(f"    Content: {entity_type} {entity_id} - {operation}")
                except:
                    pass
        else:
            print("  No pending messages")
    except Exception as e:
        print(f"\nError getting pending: {e}")
    
    # Try to read as a worker would
    print(f"\nAttempting to read messages as worker would:")
    try:
        # Use a test consumer name
        test_consumer = "test_worker_check"
        
        # Read new messages
        messages = await redis_client.xreadgroup(
            groupname=consumer_group,
            consumername=test_consumer,
            streams={operations_stream: ">"},
            count=5,
            block=1000
        )
        
        if messages:
            print(f"  Found {len(messages[0][1])} new messages")
            for msg_id, fields in messages[0][1]:
                entity_type = fields.get('entity_type', 'unknown')
                entity_id = fields.get('entity_id', 'unknown')
                operation = fields.get('operation', 'unknown')
                print(f"    {msg_id}: {entity_type} {entity_id} - {operation}")
        else:
            print(f"  No new messages available")
        
        # Read from start (unprocessed)
        unprocessed = await redis_client.xreadgroup(
            groupname=consumer_group,
            consumername=test_consumer,
            streams={operations_stream: "0"},
            count=5
        )
        
        if unprocessed:
            print(f"  Found {len(unprocessed[0][1])} unprocessed messages from start")
        else:
            print(f"  No unprocessed messages from start")
            
    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
    
    await redis_client.aclose()

if __name__ == "__main__":
    asyncio.run(main())









