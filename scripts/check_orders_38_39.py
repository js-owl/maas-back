"""Check status of orders 38 and 39"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from backend.bitrix.queue_service import bitrix_queue_service
from sqlalchemy import select
import redis.asyncio as redis
from backend.core.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_STREAM_PREFIX

async def check_redis_queue():
    """Check Redis queue for pending messages"""
    try:
        redis_client = await redis.Redis(
            host=REDIS_HOST,
            port=int(REDIS_PORT),
            db=int(REDIS_DB),
            decode_responses=True
        )
        
        # Check operations stream
        operations_stream = f"{REDIS_STREAM_PREFIX}operations"
        length = await redis_client.xlen(operations_stream)
        
        # Get pending messages
        consumer_group = "bitrix_worker"
        consumer_name = "worker_1"
        
        try:
            pending = await redis_client.xpending_range(
                operations_stream,
                consumer_group,
                min="-",
                max="+",
                count=100
            )
        except:
            pending = []
        
        # Get recent messages
        try:
            recent = await redis_client.xread({operations_stream: "0"}, count=10)
        except:
            recent = []
        
        return {
            "stream_length": length,
            "pending_count": len(pending),
            "pending": pending[:5] if pending else [],
            "recent_messages": len(recent[0][1]) if recent else 0
        }
    except Exception as e:
        return {"error": str(e)}

async def main():
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("Checking Orders 38 and 39")
        print("=" * 60)
        
        # Check orders in database
        for order_id in [38, 39]:
            print(f"\n{'='*60}")
            print(f"Order {order_id}")
            print(f"{'='*60}")
            
            result = await db.execute(
                select(models.Order).where(models.Order.order_id == order_id)
            )
            order = result.scalar_one_or_none()
            
            if not order:
                print(f"❌ Order {order_id} NOT FOUND in database!")
                continue
            
            print(f"✓ Order {order_id} found in database")
            print(f"  Status: {order.status}")
            print(f"  User ID: {order.user_id}")
            print(f"  Service: {order.service_id}")
            print(f"  Created: {order.created_at}")
            print(f"  Updated: {order.updated_at}")
            print(f"  Bitrix Deal ID: {order.bitrix_deal_id or 'NOT SET'}")
            
            # Check user
            user_result = await db.execute(
                select(models.User).where(models.User.id == order.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                print(f"  User Bitrix Contact ID: {user.bitrix_contact_id or 'NOT SET'}")
            else:
                print(f"  ❌ User {order.user_id} NOT FOUND")
            
            # Check Bitrix deal if exists
            if order.bitrix_deal_id:
                print(f"\n  Checking Bitrix deal {order.bitrix_deal_id}...")
                deal = await bitrix_client.get_deal(order.bitrix_deal_id)
                if deal:
                    print(f"  ✓ Deal {order.bitrix_deal_id} exists in Bitrix")
                    print(f"    Title: {deal.get('TITLE', 'N/A')}")
                    print(f"    Stage: {deal.get('STAGE_ID', 'N/A')}")
                    print(f"    Category: {deal.get('CATEGORY_ID', 'N/A')}")
                    print(f"    Contact ID: {deal.get('CONTACT_ID', 'NOT ATTACHED')}")
                    print(f"    Created: {deal.get('DATE_CREATE', 'N/A')}")
                    print(f"    Modified: {deal.get('DATE_MODIFY', 'N/A')}")
                else:
                    print(f"  ❌ Deal {order.bitrix_deal_id} NOT FOUND in Bitrix")
            else:
                print(f"\n  ⚠️  No Bitrix deal ID - deal may not be created yet")
        
        # Check Redis queue
        print(f"\n{'='*60}")
        print("Redis Queue Status")
        print(f"{'='*60}")
        queue_status = await check_redis_queue()
        if "error" in queue_status:
            print(f"❌ Error checking Redis: {queue_status['error']}")
        else:
            print(f"Stream length: {queue_status['stream_length']}")
            print(f"Pending messages: {queue_status['pending_count']}")
            if queue_status['pending']:
                print(f"  First few pending:")
                for msg in queue_status['pending'][:3]:
                    print(f"    - {msg}")
            print(f"Recent messages: {queue_status['recent_messages']}")
        
        print(f"\n{'='*60}")
        print("Summary")
        print(f"{'='*60}")
        print("If orders don't have Bitrix deal IDs, check:")
        print("  1. Redis queue has messages (worker may be processing)")
        print("  2. Worker logs for errors")
        print("  3. Contact creation status (deals need contacts)")

if __name__ == "__main__":
    asyncio.run(main())









