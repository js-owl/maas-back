#!/usr/bin/env python3
"""Check Redis for webhook messages related to specific deals"""
import asyncio
import json
import redis.asyncio as redis

async def check_webhooks():
    r = await redis.from_url('redis://redis:6379')
    
    # Read all messages from bitrix:webhooks stream
    messages = await r.xread({'bitrix:webhooks': '0'}, count=1000)
    
    if not messages or not messages[0][1]:
        print("No webhook messages found in Redis")
        return
    
    print(f"Total webhook messages in Redis: {len(messages[0][1])}\n")
    
    deal_61_found = False
    for msg_id, msg_data in messages[0][1]:
        try:
            # Redis stores webhook messages with fields: event_type, entity_type, entity_id, data, timestamp
            entity_id_str = msg_data.get(b'entity_id')
            event_type = msg_data.get(b'event_type', b'').decode() if msg_data.get(b'event_type') else None
            entity_type = msg_data.get(b'entity_type', b'').decode() if msg_data.get(b'entity_type') else None
            data_str = msg_data.get(b'data')
            timestamp = msg_data.get(b'timestamp', b'').decode() if msg_data.get(b'timestamp') else None
            
            entity_id = None
            if entity_id_str:
                try:
                    entity_id = int(entity_id_str.decode())
                except:
                    entity_id = None
            
            # Also check in the data field
            deal_id_from_data = None
            if data_str:
                try:
                    data = json.loads(data_str.decode())
                    deal_id_from_data = data.get('ID') or data.get('id')
                    if deal_id_from_data:
                        try:
                            deal_id_from_data = int(deal_id_from_data)
                        except:
                            pass
                except:
                    pass
            
            # Check if it's deal 57 or 61
            deal_num = entity_id or deal_id_from_data
            if deal_num in [57, 61]:
                deal_61_found = True
                print(f"=== FOUND WEBHOOK FOR DEAL {deal_num} ===")
                print(f"Message ID: {msg_id.decode()}")
                print(f"Event Type: {event_type}")
                print(f"Entity Type: {entity_type}")
                print(f"Entity ID: {entity_id}")
                print(f"Timestamp: {timestamp}")
                if data_str:
                    print(f"Data: {json.dumps(json.loads(data_str.decode()), indent=2, default=str)}")
                print()
            else:
                print(f"Webhook: entity_id={deal_num}, event_type={event_type}, entity_type={entity_type}, timestamp={timestamp}")
        except Exception as e:
            print(f"Error processing message {msg_id}: {e}")
            print(f"Raw message data keys: {list(msg_data.keys())}")
    
    if not deal_61_found:
        print("No webhook messages found for deals 57 or 61")
        print("\nAll webhook messages:")
        for msg_id, msg_data in messages[0][1]:
            try:
                payload_bytes = msg_data.get(b'payload')
                if payload_bytes:
                    payload = json.loads(payload_bytes.decode())
                    entity_id = payload.get('entity_id')
                    if not entity_id and 'data' in payload:
                        data = payload['data']
                        if isinstance(data, dict):
                            entity_id = data.get('ID') or data.get('id')
                            if not entity_id and 'FIELDS' in data:
                                entity_id = data['FIELDS'].get('ID') or data['FIELDS'].get('id')
                    print(f"  Message {msg_id.decode()}: entity_id={entity_id}, event_type={payload.get('event_type')}, entity_type={payload.get('entity_type')}")
                    if entity_id:
                        print(f"    Full payload: {json.dumps(payload, indent=4, default=str)[:500]}")
            except Exception as e:
                print(f"  Message {msg_id.decode()}: (could not parse: {e})")
                print(f"    Raw: {msg_data}")

if __name__ == "__main__":
    asyncio.run(check_webhooks())

