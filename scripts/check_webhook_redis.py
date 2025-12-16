"""Check webhook messages in Redis"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.bitrix.queue_service import bitrix_queue_service

async def check():
    redis = await bitrix_queue_service._get_redis()
    info = await redis.xinfo_stream(bitrix_queue_service.webhooks_stream)
    length = info.get("length", 0)
    last_id = info.get("last-entry", [None, {}])[0]
    print(f"Webhook stream length: {length}")
    print(f"Last ID: {last_id}")
    
    if length > 0:
        messages = await redis.xrange(
            bitrix_queue_service.webhooks_stream,
            min="-",
            max="+",
            count=5
        )
        print(f"\nRecent messages ({len(messages)}):")
        for msg_id, fields in messages[-5:]:
            print(f"  {msg_id}: {fields.get('event_type')} for {fields.get('entity_type')} {fields.get('entity_id')}")

if __name__ == "__main__":
    asyncio.run(check())






