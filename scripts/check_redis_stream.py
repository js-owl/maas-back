"""Check Redis stream for order 38"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.queue_service import bitrix_queue_service

async def main():
    stream = bitrix_queue_service.operations_stream
    print(f"Stream name: {stream}")
    
    # Get stream info
    info = await bitrix_queue_service.get_stream_info(stream)
    print(f"\nStream info:")
    print(f"  Length: {info.get('length', 0)}")
    
    # Try to read messages directly
    try:
        redis = await bitrix_queue_service._get_redis()
        
        # Read last 20 messages
        messages = await redis.xrevrange(stream, count=20)
        print(f"\nLast 20 messages in stream:")
        for msg_id, msg_data in messages:
            # Try to decode all fields
            decoded = {}
            for key, value in msg_data.items():
                if isinstance(key, bytes):
                    key_str = key.decode()
                else:
                    key_str = str(key)
                if isinstance(value, bytes):
                    try:
                        decoded[key_str] = value.decode()
                    except:
                        decoded[key_str] = str(value)
                else:
                    decoded[key_str] = value
            
            order_id = decoded.get('order_id', decoded.get('payload', {}).get('order_id', 'unknown') if isinstance(decoded.get('payload'), dict) else 'unknown')
            operation = decoded.get('operation', 'unknown')
            entity_id = decoded.get('entity_id', 'unknown')
            
            print(f"  {msg_id}: operation={operation}, entity_id={entity_id}, order_id={order_id}")
            print(f"    All fields: {list(decoded.keys())}")
            
            # Check if this is order 38
            if str(entity_id) == '38' or str(order_id) == '38':
                print(f"    *** FOUND ORDER 38 MESSAGE: {msg_id} ***")
                print(f"    Full decoded message: {decoded}")
    except Exception as e:
        print(f"Error reading messages: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

