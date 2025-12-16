"""Check why deals aren't appearing in MaaS funnel"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.database import get_db
from backend import models
from sqlalchemy import select
from backend.bitrix.queue_service import bitrix_queue_service
from backend.bitrix.funnel_manager import funnel_manager

async def check():
    print("=" * 60)
    print("Checking Deals Workflow")
    print("=" * 60)
    
    # 1. Check orders in database
    print("\n1. Orders in Database:")
    async for db in get_db():
        result = await db.execute(select(models.Order))
        orders = result.scalars().all()
        print(f"   Total orders: {len(orders)}")
        
        orders_with_deals = [o for o in orders if o.bitrix_deal_id]
        orders_without_deals = [o for o in orders if not o.bitrix_deal_id]
        
        print(f"   Orders with Bitrix deal ID: {len(orders_with_deals)}")
        print(f"   Orders without Bitrix deal ID: {len(orders_without_deals)}")
        
        if orders:
            print(f"\n   First 5 orders:")
            for o in orders[:5]:
                print(f"      Order {o.order_id}: status={o.status}, deal_id={o.bitrix_deal_id}")
        
        break
    
    # 2. Check Redis stream
    print("\n2. Redis Stream Status:")
    try:
        stream_info = await bitrix_queue_service.redis.xinfo_stream("bitrix:operations")
        length = stream_info.get("length", 0)
        print(f"   Stream length: {length} messages")
        
        if length > 0:
            # Get pending messages
            pending = await bitrix_queue_service.get_pending_messages(limit=10)
            print(f"   Pending messages: {len(pending)}")
            
            if pending:
                print(f"\n   First pending message:")
                msg = pending[0]
                print(f"      ID: {msg.get('id')}")
                print(f"      Data: {msg.get('data', {})}")
        else:
            print("   ⚠️  No messages in stream")
    except Exception as e:
        print(f"   ❌ Error checking stream: {e}")
    
    # 3. Check funnel manager
    print("\n3. Funnel Manager Status:")
    print(f"   Initialized: {funnel_manager.is_initialized()}")
    print(f"   Category ID: {funnel_manager.get_category_id()}")
    print(f"   Stage mapping: {funnel_manager.get_stage_mapping()}")
    
    # 4. Check consumer group
    print("\n4. Consumer Group Status:")
    try:
        groups = await bitrix_queue_service.redis.xinfo_groups("bitrix:operations")
        print(f"   Consumer groups: {len(groups)}")
        for group in groups:
            print(f"      Group: {group.get('name')}")
            print(f"         Consumers: {group.get('consumers', 0)}")
            print(f"         Pending: {group.get('pending', 0)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(check())







