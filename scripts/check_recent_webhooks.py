"""Check all recent webhook messages"""
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
        count=10
    )
    
    print(f"Total messages: {len(messages)}")
    print("\nAll webhook messages:")
    for msg_id, fields in messages:
        event = fields.get('event_type')
        entity = f"{fields.get('entity_type')} {fields.get('entity_id')}"
        timestamp = fields.get('timestamp', '')[:19] if fields.get('timestamp') else ''
        print(f"  {msg_id}: {event} for {entity} at {timestamp}")
        
        # Show stage info for deals
        if fields.get('entity_type') == 'deal':
            data_str = fields.get('data', '{}')
            try:
                data = json.loads(data_str)
                stage = data.get('STAGE_ID', 'N/A')
                old_stage = data.get('OLD_STAGE_ID', 'N/A')
                print(f"    Stage: {old_stage} -> {stage}")

if __name__ == "__main__":
    asyncio.run(check())






