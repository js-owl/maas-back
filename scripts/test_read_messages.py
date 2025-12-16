"""Test reading messages from Redis"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.bitrix.queue_service import bitrix_queue_service

async def test():
    print("Testing message reading...")
    try:
        print("Step 1: Getting Redis connection...")
        redis = await bitrix_queue_service._get_redis()
        print("Step 2: Redis connection obtained")
        
        print("Step 3: Ensuring consumer group...")
        await bitrix_queue_service._ensure_consumer_group(bitrix_queue_service.operations_stream)
        print("Step 4: Consumer group ensured")
        
        print("Step 5: Reading messages...")
        msgs = await asyncio.wait_for(
            bitrix_queue_service.get_pending_messages(
                bitrix_queue_service.operations_stream,
                count=5,
                block_ms=0
            ),
            timeout=5.0
        )
        print(f"Got {len(msgs)} messages")
        if msgs:
            print(f"First message: {msgs[0]}")
    except asyncio.TimeoutError:
        print("Timeout: Operation took too long")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            redis = await bitrix_queue_service._get_redis()
            await redis.close()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test())

