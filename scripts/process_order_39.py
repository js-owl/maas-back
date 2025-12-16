"""Manually process order 39 update message"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.bitrix.worker import bitrix_worker
from backend.bitrix.queue_service import bitrix_queue_service
from backend.database import AsyncSessionLocal

async def process_message():
    print("Fetching messages from Redis...")
    async with AsyncSessionLocal() as db:
        # Try reading from beginning (0) to catch messages that existed before consumer group
        redis = await bitrix_queue_service._get_redis()
        await bitrix_queue_service._ensure_consumer_group(bitrix_queue_service.operations_stream)
        
        # Read from beginning
        messages = await redis.xreadgroup(
            groupname=bitrix_queue_service.consumer_group,
            consumername=bitrix_queue_service.consumer_name,
            streams={bitrix_queue_service.operations_stream: "0"},
            count=1
        )
        
        msgs = []
        for stream, stream_messages in messages:
            for message_id, fields in stream_messages:
                msgs.append({
                    "id": message_id,
                    "stream": stream,
                    **fields
                })
        print(f"Found {len(msgs)} messages")
        
        if msgs:
            msg = msgs[0]
            print(f"\nProcessing message: {msg.get('id')}")
            print(f"Entity: {msg.get('entity_type')} {msg.get('entity_id')}")
            print(f"Operation: {msg.get('operation')}")
            
            result = await bitrix_worker.process_operation_message(msg, db)
            print(f"\nProcess result: {result}")
            
            if result:
                # Acknowledge the message
                await bitrix_queue_service.acknowledge_message(
                    bitrix_queue_service.operations_stream,
                    msg['id']
                )
                print("Message acknowledged")
            else:
                print("Message processing failed, will be retried")
        else:
            print("No messages found")
    
    # Close Redis connection
    redis = await bitrix_queue_service._get_redis()
    await redis.aclose()

if __name__ == "__main__":
    asyncio.run(process_message())

