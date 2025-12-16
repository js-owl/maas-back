"""Check webhook messages for deal 59"""
import asyncio
import sys
import json
sys.path.insert(0, '/app')

from backend.bitrix.queue_service import bitrix_queue_service

async def check():
    redis = await bitrix_queue_service._get_redis()
    messages = await redis.xrange(
        bitrix_queue_service.webhooks_stream,
        min="-",
        max="+",
        count=100
    )
    
    print(f"Total webhook messages: {len(messages)}")
    print("\nWebhook messages for deal 59:")
    found = False
    for msg_id, fields in messages:
        entity_id = fields.get('entity_id')
        if entity_id and str(entity_id) == '59':
            found = True
            event = fields.get('event_type')
            timestamp = fields.get('timestamp', '')
            print(f"\n  Message ID: {msg_id}")
            print(f"  Event: {event}")
            print(f"  Timestamp: {timestamp}")
            
            # Show deal data
            data_str = fields.get('data', '{}')
            try:
                data = json.loads(data_str)
                print(f"  Stage: {data.get('STAGE_ID', 'N/A')}")
                print(f"  Old Stage: {data.get('OLD_STAGE_ID', 'N/A')}")
                print(f"  Category: {data.get('CATEGORY_ID', 'N/A')}")
                print(f"  Amount: {data.get('OPPORTUNITY', 'N/A')}")
                print(f"  Contact: {data.get('CONTACT_ID', 'N/A')}")
                print(f"  Title: {data.get('TITLE', 'N/A')}")
            except Exception as e:
                print(f"  Data: {data_str[:200]}")
                print(f"  Error parsing: {e}")
    
    if not found:
        print("  No webhook messages found for deal 59")
    
    # Check if there's an order with deal 59
    print("\n" + "=" * 80)
    print("Checking for order with deal 59...")
    from backend.database import get_db
    from backend import models
    from sqlalchemy import select
    
    async for db in get_db():
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id == 59)
        )
        order = result.scalar_one_or_none()
        
        if order:
            print(f"\nOrder {order.order_id}:")
            print(f"  Status: {order.status}")
            print(f"  Total Price: {order.total_price}")
            print(f"  Updated At: {order.updated_at}")
        else:
            print("\n  No order found with deal 59")
        break

if __name__ == "__main__":
    asyncio.run(check())






