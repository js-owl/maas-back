"""Clear old messages from Redis streams"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.bitrix.queue_service import bitrix_queue_service
from backend.utils.logging import get_logger

logger = get_logger(__name__)

async def clear_messages():
    """Clear all messages from the operations stream"""
    try:
        redis = await bitrix_queue_service._get_redis()
        
        stream_name = bitrix_queue_service.operations_stream
        print(f"Checking stream: {stream_name}")
        
        # Get stream info
        info = await redis.xinfo_stream(stream_name)
        length = info.get('length', 0)
        print(f"Current stream length: {length}")
        
        if length == 0:
            print("Stream is already empty")
            return
        
        # Ask for confirmation
        print(f"\nWARNING: This will delete ALL {length} messages from {stream_name}")
        print("This action cannot be undone!")
        
        # For script, we'll proceed (in production, you'd want confirmation)
        # Delete the stream entirely
        deleted = await redis.delete(stream_name)
        
        if deleted:
            print(f"✓ Successfully deleted stream {stream_name}")
            print("All messages have been cleared")
        else:
            print(f"✗ Failed to delete stream {stream_name}")
            
        # Also check and optionally clear webhooks stream
        webhook_stream = bitrix_queue_service.webhooks_stream
        webhook_info = await redis.xinfo_stream(webhook_stream)
        webhook_length = webhook_info.get('length', 0)
        
        if webhook_length > 0:
            print(f"\nWebhooks stream has {webhook_length} messages")
            deleted_webhooks = await redis.delete(webhook_stream)
            if deleted_webhooks:
                print(f"✓ Also cleared webhooks stream")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            redis = await bitrix_queue_service._get_redis()
            await redis.aclose()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(clear_messages())

