"""Check why messages aren't being processed"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.queue_service import bitrix_queue_service

async def main():
    stream = bitrix_queue_service.operations_stream
    print(f"Stream: {stream}")
    
    try:
        redis = await bitrix_queue_service._get_redis()
        
        # Try to read with ">" (new messages)
        print("\nTrying to read new messages with '>':")
        try:
            messages = await redis.xreadgroup(
                groupname=bitrix_queue_service.consumer_group,
                consumername=bitrix_queue_service.consumer_name,
                streams={stream: ">"},
                count=5,
                block=1000
            )
            print(f"  Messages read: {len(messages)}")
            for stream_name, stream_messages in messages:
                print(f"  Stream: {stream_name}, Messages: {len(stream_messages)}")
                for msg_id, msg_data in stream_messages:
                    entity_id = msg_data.get(b'entity_id', b'unknown').decode() if isinstance(msg_data.get(b'entity_id'), bytes) else msg_data.get('entity_id', 'unknown')
                    print(f"    {msg_id}: entity_id={entity_id}")
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Check consumer group info
        print("\nConsumer group info:")
        try:
            groups = await redis.xinfo_groups(stream)
            for group in groups:
                print(f"  {group}")
        except Exception as e:
            print(f"  Error: {e}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())









