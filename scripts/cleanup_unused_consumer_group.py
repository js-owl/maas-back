"""Clean up unused bitrix_worker (singular) consumer group"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import redis.asyncio as redis
from backend.core.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_STREAM_PREFIX

async def main():
    redis_client = await redis.Redis(
        host=REDIS_HOST,
        port=int(REDIS_PORT),
        db=int(REDIS_DB),
        decode_responses=True
    )
    
    operations_stream = f"{REDIS_STREAM_PREFIX}operations"
    unused_group = "bitrix_worker"  # Singular - unused
    
    print("=" * 60)
    print("Cleaning up unused consumer group")
    print("=" * 60)
    
    try:
        # Check if group exists
        groups = await redis_client.xinfo_groups(operations_stream)
        found = False
        for group in groups:
            if group['name'] == unused_group:
                found = True
                print(f"\nFound unused group: {unused_group}")
                print(f"  Consumers: {group['consumers']}")
                print(f"  Pending: {group['pending']}")
                break
        
        if not found:
            print(f"\nGroup '{unused_group}' not found - nothing to clean up")
            await redis_client.aclose()
            return
        
        # Get consumers in the group
        consumers = await redis_client.xinfo_consumers(operations_stream, unused_group)
        print(f"\nConsumers in group: {len(consumers)}")
        
        # Delete the consumer group
        # Note: We need to delete consumers first, then the group
        # But Redis doesn't have a direct way to delete a group with pending messages
        # We'll just delete the consumers
        
        for consumer in consumers:
            consumer_name = consumer['name']
            pending = consumer['pending']
            print(f"  Consumer: {consumer_name}, Pending: {pending}")
        
        # Delete the group (this will fail if there are pending messages)
        try:
            await redis_client.xgroup_destroy(operations_stream, unused_group)
            print(f"\n✓ Deleted consumer group '{unused_group}'")
        except Exception as e:
            error_str = str(e)
            if "pending" in error_str.lower():
                print(f"\n⚠️  Cannot delete group - has pending messages")
                print(f"   You may need to acknowledge or delete pending messages first")
                print(f"   Or just leave it - it won't interfere with the active group")
            else:
                print(f"\n⚠️  Error deleting group: {e}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await redis_client.aclose()

if __name__ == "__main__":
    asyncio.run(main())









