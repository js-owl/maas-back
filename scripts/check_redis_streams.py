#!/usr/bin/env python3
"""Check Redis streams for Bitrix operations and webhooks"""
import asyncio
import json
import redis.asyncio as redis

async def check_streams():
    r = await redis.from_url('redis://redis:6379')
    
    # Find all Bitrix-related streams
    streams = await r.keys('bitrix:*')
    print(f"Found {len(streams)} Bitrix streams:\n")
    
    for stream_key in streams:
        stream_name = stream_key.decode()
        length = await r.xlen(stream_name)
        print(f"Stream: {stream_name}")
        print(f"  Total messages: {length}")
        
        if length > 0:
            # Get last 10 messages
            messages = await r.xread({stream_name: '0'}, count=10)
            if messages and messages[0][1]:
                print(f"  Recent messages (last 10):")
                for msg_id, msg_data in list(messages[0][1])[-10:]:
                    # Decode message data
                    decoded = {}
                    for key, value in msg_data.items():
                        try:
                            if isinstance(value, bytes):
                                decoded[key.decode()] = value.decode()
                            else:
                                decoded[key] = value
                        except:
                            decoded[key] = str(value)
                    
                    # Show relevant fields
                    entity_id = decoded.get('entity_id', decoded.get('deal_id', 'N/A'))
                    event_type = decoded.get('event_type', decoded.get('operation', 'N/A'))
                    timestamp = decoded.get('timestamp', 'N/A')
                    
                    print(f"    [{msg_id.decode()}] entity_id={entity_id}, event={event_type}, time={timestamp}")
        print()

if __name__ == "__main__":
    asyncio.run(check_streams())






