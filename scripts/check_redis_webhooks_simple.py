"""Simple script to check Redis for ONCRMDEALUPDATE messages - writes to file"""
import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def check():
    output = []
    output.append("=" * 80)
    output.append("CHECKING REDIS FOR ONCRMDEALUPDATE MESSAGES")
    output.append("=" * 80)
    
    try:
        from backend.bitrix.queue_service import bitrix_queue_service
        
        redis = await bitrix_queue_service._get_redis()
        stream_name = bitrix_queue_service.webhooks_stream
        
        output.append(f"\nStream: {stream_name}")
        
        # Get stream info
        try:
            info = await redis.xinfo_stream(stream_name)
            length = info.get("length", 0)
            output.append(f"Total messages: {length}")
        except Exception as e:
            output.append(f"Error getting stream info: {e}")
            length = 0
        
        if length == 0:
            output.append("\nNo messages in webhook stream")
        else:
            # Read messages
            messages = await redis.xrange(stream_name, min="-", max="+", count=50)
            output.append(f"\nFound {len(messages)} message(s) in stream")
            
            # Filter for ONCRMDEALUPDATE
            oncrm_messages = []
            for msg_id, fields in messages:
                event_type = fields.get("event_type", "").upper()
                if "ONCRMDEALUPDATE" in event_type or "DEAL_UPDATED" in event_type:
                    oncrm_messages.append((msg_id, fields))
            
            if oncrm_messages:
                output.append(f"\nFound {len(oncrm_messages)} ONCRMDEALUPDATE message(s):")
                for i, (msg_id, fields) in enumerate(oncrm_messages[-10:], 1):
                    output.append(f"\nMessage {i}:")
                    output.append(f"  ID: {msg_id}")
                    output.append(f"  Event: {fields.get('event_type', 'N/A')}")
                    output.append(f"  Entity: {fields.get('entity_type', 'N/A')} {fields.get('entity_id', 'N/A')}")
                    output.append(f"  Timestamp: {fields.get('timestamp', 'N/A')}")
                    
                    # Parse data
                    data_str = fields.get('data', '{}')
                    try:
                        data = json.loads(data_str) if isinstance(data_str, str) else data_str
                        output.append(f"  Deal ID: {data.get('ID', data.get('id', 'N/A'))}")
                        output.append(f"  Stage: {data.get('STAGE_ID', 'N/A')}")
                        output.append(f"  Old Stage: {data.get('OLD_STAGE_ID', 'N/A')}")
                        output.append(f"  Category: {data.get('CATEGORY_ID', 'N/A')}")
                    except:
                        output.append(f"  Data: {str(data_str)[:100]}")
            else:
                output.append(f"\nNo ONCRMDEALUPDATE messages found")
                output.append(f"Showing recent messages:")
                for i, (msg_id, fields) in enumerate(messages[-5:], 1):
                    output.append(f"  {i}. {msg_id}: {fields.get('event_type', 'N/A')} - {fields.get('entity_type', 'N/A')} {fields.get('entity_id', 'N/A')}")
        
        # Check consumer groups
        try:
            groups = await redis.xinfo_groups(stream_name)
            output.append(f"\nConsumer Groups:")
            for group in groups:
                output.append(f"  {group.get('name', 'N/A')}: {group.get('pending', 0)} pending, {group.get('consumers', 0)} consumers")
        except:
            pass
        
    except Exception as e:
        output.append(f"\nError: {e}")
        import traceback
        output.append(traceback.format_exc())
    
    result = "\n".join(output)
    print(result)
    
    # Write to file
    with open("redis_webhooks_check.txt", "w", encoding="utf-8") as f:
        f.write(result)
    
    return result

if __name__ == "__main__":
    asyncio.run(check())





