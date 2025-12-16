"""Check Redis for ONCRMDEALUPDATE webhook messages from Bitrix"""
import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.queue_service import bitrix_queue_service

async def check_oncrmdealuPDATE_messages():
    """Check Redis webhook stream for ONCRMDEALUPDATE messages"""
    print("=" * 80)
    print("CHECKING REDIS FOR ONCRMDEALUPDATE MESSAGES")
    print("=" * 80)
    
    try:
        redis = await bitrix_queue_service._get_redis()
        
        # Get stream info
        stream_name = bitrix_queue_service.webhooks_stream
        print(f"\n📊 Stream: {stream_name}")
        
        try:
            info = await redis.xinfo_stream(stream_name)
            length = info.get("length", 0)
            last_id = info.get("last-entry", [None, {}])
            last_id_str = last_id[0] if last_id[0] else "N/A"
            
            print(f"   Total messages: {length}")
            print(f"   Last message ID: {last_id_str}")
        except Exception as e:
            print(f"   ⚠️  Could not get stream info: {e}")
            length = 0
        
        if length == 0:
            print(f"\n   ℹ️  No messages in webhook stream")
            return
        
        # Read all messages (or last 100)
        print(f"\n🔍 Reading messages from stream...")
        messages = await redis.xrange(
            stream_name,
            min="-",
            max="+",
            count=100  # Limit to last 100 messages
        )
        
        print(f"   Found {len(messages)} message(s)")
        
        # Filter for ONCRMDEALUPDATE or deal_updated events
        oncrmdealuPDATE_messages = []
        deal_messages = []
        
        for msg_id, fields in messages:
            event_type = fields.get("event_type", "")
            entity_type = fields.get("entity_type", "")
            
            # Check for ONCRMDEALUPDATE or deal_updated
            if "ONCRMDEALUPDATE" in event_type.upper() or "deal_updated" in event_type.lower():
                oncrmdealuPDATE_messages.append((msg_id, fields))
            elif entity_type.lower() == "deal":
                deal_messages.append((msg_id, fields))
        
        print(f"\n📋 Results:")
        print(f"   ONCRMDEALUPDATE/deal_updated messages: {len(oncrmdealuPDATE_messages)}")
        print(f"   Other deal messages: {len(deal_messages)}")
        
        if oncrmdealuPDATE_messages:
            print(f"\n✅ Found {len(oncrmdealuPDATE_messages)} ONCRMDEALUPDATE message(s):")
            for i, (msg_id, fields) in enumerate(oncrmdealuPDATE_messages[-10:], 1):  # Show last 10
                print(f"\n   Message {i}:")
                print(f"     ID: {msg_id}")
                print(f"     Event Type: {fields.get('event_type', 'N/A')}")
                print(f"     Entity Type: {fields.get('entity_type', 'N/A')}")
                print(f"     Entity ID: {fields.get('entity_id', 'N/A')}")
                print(f"     Timestamp: {fields.get('timestamp', 'N/A')}")
                
                # Parse data if available
                data_str = fields.get('data', '{}')
                try:
                    if isinstance(data_str, str):
                        data = json.loads(data_str)
                    else:
                        data = data_str
                    
                    print(f"     Deal Data:")
                    print(f"       Deal ID: {data.get('ID', data.get('id', 'N/A'))}")
                    print(f"       Stage ID: {data.get('STAGE_ID', data.get('stage_id', 'N/A'))}")
                    print(f"       Old Stage ID: {data.get('OLD_STAGE_ID', data.get('old_stage_id', 'N/A'))}")
                    print(f"       Category ID: {data.get('CATEGORY_ID', data.get('category_id', 'N/A'))}")
                    print(f"       Title: {data.get('TITLE', data.get('title', 'N/A'))}")
                    print(f"       Amount: {data.get('OPPORTUNITY', data.get('opportunity', 'N/A'))}")
                except Exception as e:
                    print(f"       Data: {str(data_str)[:200]}")
        
        elif deal_messages:
            print(f"\n   ℹ️  Found {len(deal_messages)} deal message(s) (not ONCRMDEALUPDATE):")
            for i, (msg_id, fields) in enumerate(deal_messages[-5:], 1):
                print(f"     {i}. Message {msg_id}: {fields.get('event_type', 'N/A')} for deal {fields.get('entity_id', 'N/A')}")
        else:
            print(f"\n   ℹ️  No ONCRMDEALUPDATE or deal messages found")
            print(f"   Showing all recent messages:")
            for i, (msg_id, fields) in enumerate(messages[-5:], 1):
                print(f"     {i}. Message {msg_id}:")
                print(f"        Event: {fields.get('event_type', 'N/A')}")
                print(f"        Entity: {fields.get('entity_type', 'N/A')} {fields.get('entity_id', 'N/A')}")
        
        # Check consumer group status
        print(f"\n📊 Consumer Group Status:")
        try:
            groups = await redis.xinfo_groups(stream_name)
            for group in groups:
                group_name = group.get("name", "N/A")
                pending = group.get("pending", 0)
                consumers = group.get("consumers", 0)
                print(f"   Group: {group_name}")
                print(f"     Pending messages: {pending}")
                print(f"     Consumers: {consumers}")
        except Exception as e:
            print(f"   ⚠️  Could not get consumer group info: {e}")
        
    except Exception as e:
        print(f"\n❌ Error checking Redis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_oncrmdealuPDATE_messages())





