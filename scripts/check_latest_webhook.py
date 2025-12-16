"""Check latest webhook message details"""
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
        count=1
    )
    
    if messages:
        msg_id, fields = messages[-1]
        print(f"Latest message ID: {msg_id}")
        print(f"Event: {fields.get('event_type')}")
        print(f"Entity: {fields.get('entity_type')} {fields.get('entity_id')}")
        print(f"Timestamp: {fields.get('timestamp')}")
        
        data_str = fields.get('data', '{}')
        try:
            data = json.loads(data_str)
            print(f"\nDeal Data:")
            print(f"  Stage: {data.get('STAGE_ID')}")
            print(f"  Old Stage: {data.get('OLD_STAGE_ID')}")
            print(f"  Category: {data.get('CATEGORY_ID')}")
            print(f"  Amount: {data.get('OPPORTUNITY')}")
        except:
            print(f"Data: {data_str[:200]}")
    else:
        print("No webhook messages found")
    
    # Check consumer group
    try:
        groups = await redis.xinfo_groups(bitrix_queue_service.webhooks_stream)
        for group in groups:
            pending = group.get("pending", 0)
            print(f"\nPending messages: {pending}")
    except:
        pass

if __name__ == "__main__":
    asyncio.run(check())






