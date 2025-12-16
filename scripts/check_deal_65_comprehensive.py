"""Comprehensive check for deal 65 webhook activity"""
import subprocess
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def check_redis_comprehensive():
    """Check Redis stream comprehensively"""
    try:
        from backend.bitrix.queue_service import bitrix_queue_service
        
        print("=" * 80)
        print("COMPREHENSIVE REDIS STREAM CHECK")
        print("=" * 80)
        
        redis = await bitrix_queue_service._get_redis()
        stream_name = "bitrix:webhooks"
        
        # Get stream info
        try:
            info = await redis.xinfo_stream(stream_name)
            length = info.get("length", 0)
            print(f"\nStream: {stream_name}")
            print(f"Total messages: {length}")
        except Exception as e:
            print(f"Error getting stream info: {e}")
            return
        
        if length == 0:
            print("\n⚠️  Stream is empty")
            return
        
        # Read ALL messages
        print(f"\nReading all {length} messages...")
        messages = await redis.xrange(
            stream_name,
            min="-",
            max="+",
            count=length if length < 1000 else 1000
        )
        
        print(f"Found {len(messages)} messages")
        
        # Check for deal 65
        deal_65_messages = []
        deal_65_in_data = []
        
        for msg_id, fields in messages:
            entity_id = fields.get('entity_id')
            
            # Check entity_id
            if entity_id and str(entity_id) == '65':
                deal_65_messages.append((msg_id, fields))
            
            # Check data field
            if 'data' in fields:
                try:
                    data = json.loads(fields['data']) if isinstance(fields['data'], str) else fields['data']
                    deal_id = data.get('ID') or data.get('id')
                    if deal_id and str(deal_id) == '65':
                        deal_65_in_data.append((msg_id, fields))
                except:
                    pass
        
        print(f"\n🔍 Results:")
        print(f"   Messages with entity_id = 65: {len(deal_65_messages)}")
        print(f"   Messages with ID = 65 in data: {len(deal_65_in_data)}")
        
        if deal_65_messages:
            print(f"\n✅ Found {len(deal_65_messages)} webhook message(s) for deal 65:")
            for msg_id, fields in deal_65_messages:
                print(f"\n   Message ID: {msg_id}")
                print(f"   Event: {fields.get('event_type')}")
                print(f"   Entity: {fields.get('entity_type')} {fields.get('entity_id')}")
                print(f"   Timestamp: {fields.get('timestamp')}")
                if 'data' in fields:
                    try:
                        data = json.loads(fields['data']) if isinstance(fields['data'], str) else fields['data']
                        print(f"   Data: {json.dumps(data, indent=6)[:300]}")
                    except:
                        print(f"   Data (raw): {fields['data'][:200]}")
        
        if deal_65_in_data and not deal_65_messages:
            print(f"\n⚠️  Found {len(deal_65_in_data)} message(s) with deal 65 in data but not entity_id:")
            for msg_id, fields in deal_65_in_data:
                print(f"   Message ID: {msg_id}")
        
        # Show all unique deal IDs
        all_deal_ids = set()
        for msg_id, fields in messages:
            entity_id = fields.get('entity_id')
            if entity_id and fields.get('entity_type', '').lower() == 'deal':
                all_deal_ids.add(entity_id)
            if 'data' in fields:
                try:
                    data = json.loads(fields['data']) if isinstance(fields['data'], str) else fields['data']
                    deal_id = data.get('ID') or data.get('id')
                    if deal_id:
                        all_deal_ids.add(str(deal_id))
                except:
                    pass
        
        print(f"\n📊 All deal IDs in stream: {sorted(all_deal_ids)}")
        
    except ImportError:
        print("Cannot import backend modules - running outside container")
        print("Try running: docker exec backend python3 /app/check_deal_65_comprehensive.py")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def check_docker_logs_comprehensive():
    """Check Docker logs more comprehensively"""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE DOCKER LOGS CHECK")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            ["docker", "logs", "backend"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30
        )
        
        logs = result.stdout
        lines = logs.split('\n')
        
        # Find all entries related to 65 or 41
        relevant_entries = []
        for i, line in enumerate(lines, 1):
            # Look for deal 65, entity_id 65, order 41
            if re.search(r'\b(65|41)\b', line):
                # Exclude false positives
                if not re.search(r'0\.65|\.65ms|65ms|Duration.*65|port.*65|:65[0-9]', line):
                    if any(keyword in line.lower() for keyword in ['deal', 'webhook', 'entity', 'order', 'bitrix']):
                        relevant_entries.append((i, line.strip()))
        
        print(f"\nFound {len(relevant_entries)} potentially relevant entries")
        
        if relevant_entries:
            print(f"\nRelevant entries (showing first 30):")
            for line_num, line in relevant_entries[:30]:
                print(f"   Line {line_num}: {line[:150]}")
        else:
            print("\n⚠️  No relevant entries found")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import asyncio
    import re
    
    asyncio.run(check_redis_comprehensive())
    check_docker_logs_comprehensive()


