"""Check consumer group status"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.queue_service import bitrix_queue_service

async def main():
    stream = bitrix_queue_service.operations_stream
    print(f"Stream: {stream}")
    print(f"Consumer group: {bitrix_queue_service.consumer_group}")
    print(f"Consumer name: {bitrix_queue_service.consumer_name}")
    
    try:
        redis = await bitrix_queue_service._get_redis()
        
        # Check consumer group info
        try:
            groups = await redis.xinfo_groups(stream)
            print(f"\nConsumer groups:")
            for group in groups:
                print(f"  {group}")
        except Exception as e:
            print(f"\nError getting consumer groups: {e}")
        
        # Check pending messages
        try:
            pending = await redis.xpending_range(
                name=stream,
                groupname=bitrix_queue_service.consumer_group,
                min="-",
                max="+",
                count=10
            )
            print(f"\nPending messages in consumer group: {len(pending)}")
            for msg in pending[:5]:
                print(f"  {msg}")
        except Exception as e:
            print(f"\nError getting pending messages: {e}")
        
        # Try to read from consumer group
        try:
            messages = await redis.xreadgroup(
                groupname=bitrix_queue_service.consumer_group,
                consumername=bitrix_queue_service.consumer_name,
                streams={stream: "0"},
                count=5,
                block=1000
            )
            print(f"\nMessages read from consumer group: {len(messages)}")
            for stream_name, stream_messages in messages:
                print(f"  Stream: {stream_name}, Messages: {len(stream_messages)}")
                for msg_id, msg_data in stream_messages[:3]:
                    entity_id = msg_data.get(b'entity_id', b'unknown').decode() if isinstance(msg_data.get(b'entity_id'), bytes) else msg_data.get('entity_id', 'unknown')
                    print(f"    {msg_id}: entity_id={entity_id}")
        except Exception as e:
            print(f"\nError reading from consumer group: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())









