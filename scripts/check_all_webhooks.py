"""Check all webhook messages in Redis with details"""
import asyncio
import sys
import json
from datetime import datetime
sys.path.insert(0, '/app')

from backend.bitrix.queue_service import bitrix_queue_service

async def check():
    redis = await bitrix_queue_service._get_redis()
    
    # Get all messages
    messages = await redis.xrange(
        bitrix_queue_service.webhooks_stream,
        min="-",
        max="+",
        count=100
    )
    
    print("=" * 80)
    print(f"All Webhook Messages in Redis: {len(messages)} total")
    print("=" * 80)
    
    deals = {}
    for msg_id, fields in messages:
        entity_id = fields.get('entity_id')
        event_type = fields.get('event_type', 'unknown')
        timestamp = fields.get('timestamp', '')
        
        # Parse timestamp
        try:
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_str = 'unknown'
        except:
            time_str = timestamp[:19] if timestamp else 'unknown'
        
        # Get deal data
        data_str = fields.get('data', '{}')
        try:
            data = json.loads(data_str)
            stage = data.get('STAGE_ID', 'N/A')
            old_stage = data.get('OLD_STAGE_ID', 'N/A')
            category = data.get('CATEGORY_ID', 'N/A')
        except:
            stage = 'N/A'
            old_stage = 'N/A'
            category = 'N/A'
        
        if entity_id:
            if entity_id not in deals:
                deals[entity_id] = []
            deals[entity_id].append({
                'msg_id': msg_id,
                'event': event_type,
                'time': time_str,
                'stage': stage,
                'old_stage': old_stage,
                'category': category
            })
    
    # Print by deal
    print(f"\nWebhooks by Deal ID:")
    for deal_id in sorted(deals.keys(), key=lambda x: int(x) if str(x).isdigit() else 0):
        webhooks = deals[deal_id]
        print(f"\n  Deal {deal_id}: {len(webhooks)} webhook(s)")
        for wh in webhooks:
            print(f"    - {wh['time']}: {wh['event']}")
            print(f"      Stage: {wh['old_stage']} -> {wh['stage']}")
            print(f"      Category: {wh['category']}")
            print(f"      Message ID: {wh['msg_id']}")
    
    print("\n" + "=" * 80)
    print(f"Summary: {len(deals)} unique deals with webhooks")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(check())






