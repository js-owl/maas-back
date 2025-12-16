#!/usr/bin/env python3
"""Check Redis for update operations"""
import asyncio
import redis.asyncio as redis

async def check_updates():
    r = await redis.from_url('redis://redis:6379')
    
    # Check operations stream for updates
    messages = await r.xread({'bitrix:operations': '0'}, count=200)
    
    if not messages or not messages[0][1]:
        print("No operations found")
        return
    
    updates = []
    for msg_id, msg_data in messages[0][1]:
        operation = msg_data.get(b'operation', b'').decode() if msg_data.get(b'operation') else ''
        if 'update' in operation.lower():
            entity_id = msg_data.get(b'entity_id', b'N/A').decode() if msg_data.get(b'entity_id') else 'N/A'
            timestamp = msg_data.get(b'timestamp', b'N/A').decode() if msg_data.get(b'timestamp') else 'N/A'
            updates.append((entity_id, operation, timestamp, msg_id))
    
    print(f"Total update operations: {len(updates)}\n")
    
    if updates:
        print("Recent update operations:")
        for entity_id, operation, timestamp, msg_id in updates[-20:]:
            print(f"  Deal {entity_id}: {operation} at {timestamp} (msg_id: {msg_id.decode()})")
    else:
        print("No update operations found in operations stream")
    
    # Also check webhook stream
    print("\n" + "="*50)
    print("Webhook stream (deal updates from Bitrix):")
    webhook_messages = await r.xread({'bitrix:webhooks': '0'}, count=100)
    if webhook_messages and webhook_messages[0][1]:
        print(f"Total webhook messages: {len(webhook_messages[0][1])}")
        for msg_id, msg_data in webhook_messages[0][1]:
            entity_id = msg_data.get(b'entity_id', b'N/A').decode() if msg_data.get(b'entity_id') else 'N/A'
            event_type = msg_data.get(b'event_type', b'N/A').decode() if msg_data.get(b'event_type') else 'N/A'
            timestamp = msg_data.get(b'timestamp', b'N/A').decode() if msg_data.get(b'timestamp') else 'N/A'
            print(f"  Deal {entity_id}: {event_type} at {timestamp}")

if __name__ == "__main__":
    asyncio.run(check_updates())






