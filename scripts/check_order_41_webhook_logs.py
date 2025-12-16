"""Check logs for order 41 (deal 65) webhook changes from Bitrix"""
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import asyncio

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.queue_service import bitrix_queue_service

def check_docker_logs():
    """Check Docker container logs for webhook entries related to deal 65"""
    print("=" * 80)
    print("CHECKING DOCKER CONTAINER LOGS FOR DEAL 65 WEBHOOKS")
    print("=" * 80)
    
    try:
        # Check if Docker is available
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            print("\n⚠️  Docker not available or containers not running")
            return []
        
        # Check backend container logs
        print("\n📋 Checking backend container logs...")
        result = subprocess.run(
            ["docker", "logs", "backend", "--tail", "1000"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"  ❌ Error getting Docker logs: {result.stderr}")
            return []
        
        logs = result.stdout
        lines = logs.split('\n')
        
        # Search for deal 65, order 41, or webhook entries
        relevant_lines = []
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in [
                'deal.*65', 'entity_id.*65', 'deal 65',
                'order.*41', 'order 41',
                'webhook.*65', 'webhook.*41',
                'deal_updated.*65', 'oncrmdealuPDATE.*65'
            ]):
                # Also check for exact matches
                if '65' in line and ('deal' in line_lower or 'entity_id' in line_lower or 'webhook' in line_lower):
                    relevant_lines.append((i, line.strip()))
                elif '41' in line and ('order' in line_lower or 'webhook' in line_lower):
                    relevant_lines.append((i, line.strip()))
        
        # Also search for webhook entries that might contain deal 65
        print(f"\n🔍 Found {len(relevant_lines)} potentially relevant log entries")
        
        # Show webhook-related entries
        webhook_entries = []
        for i, line in enumerate(lines, 1):
            if 'webhook' in line.lower() and ('deal' in line.lower() or 'entity_id' in line.lower()):
                webhook_entries.append((i, line.strip()))
        
        print(f"   Webhook entries found: {len(webhook_entries)}")
        
        if relevant_lines:
            print(f"\n📄 Relevant log entries (last 20):")
            for line_num, line in relevant_lines[-20:]:
                print(f"   Line {line_num}: {line[:150]}")
        
        if webhook_entries:
            print(f"\n📄 Recent webhook entries (last 10):")
            for line_num, line in webhook_entries[-10:]:
                print(f"   Line {line_num}: {line[:150]}")
        
        return relevant_lines
        
    except FileNotFoundError:
        print("\n⚠️  Docker command not found")
        return []
    except subprocess.TimeoutExpired:
        print("\n⚠️  Timeout getting Docker logs")
        return []
    except Exception as e:
        print(f"\n❌ Error checking Docker logs: {e}")
        import traceback
        traceback.print_exc()
        return []

async def check_redis_webhooks():
    """Check Redis stream for webhook messages related to deal 65"""
    print("\n" + "=" * 80)
    print("CHECKING REDIS STREAM FOR DEAL 65 WEBHOOKS")
    print("=" * 80)
    
    try:
        stream_name = "bitrix:webhooks"
        
        # Get stream info
        stream_info = await bitrix_queue_service.get_stream_info(stream_name)
        if not stream_info:
            print(f"\n⚠️  Stream {stream_name} not found or empty")
            return []
        
        print(f"\n📊 Stream Info:")
        print(f"   Stream: {stream_name}")
        print(f"   Length: {stream_info.get('length', 0)} messages")
        
        # Read recent messages
        messages = await bitrix_queue_service.read_stream_messages(
            stream_name,
            count=100
        )
        
        if not messages:
            print(f"\n⚠️  No messages found in stream")
            return []
        
        print(f"\n🔍 Searching {len(messages)} messages for deal 65 / order 41...")
        
        relevant_messages = []
        for msg_id, fields in messages:
            entity_id = fields.get('entity_id')
            entity_type = fields.get('entity_type', '').lower()
            event_type = fields.get('event_type', '').lower()
            
            # Check if this is deal 65
            if entity_id and str(entity_id) == '65' and entity_type == 'deal':
                relevant_messages.append((msg_id, fields))
            # Also check data field for deal ID 65
            elif 'data' in fields:
                try:
                    data = json.loads(fields['data']) if isinstance(fields['data'], str) else fields['data']
                    deal_id = data.get('ID') or data.get('id')
                    if deal_id and str(deal_id) == '65':
                        relevant_messages.append((msg_id, fields))
                except (json.JSONDecodeError, TypeError):
                    pass
        
        print(f"\n✅ Found {len(relevant_messages)} webhook message(s) for deal 65")
        
        if relevant_messages:
            for msg_id, fields in relevant_messages:
                print(f"\n📨 Message ID: {msg_id}")
                print(f"   Event Type: {fields.get('event_type', 'N/A')}")
                print(f"   Entity Type: {fields.get('entity_type', 'N/A')}")
                print(f"   Entity ID: {fields.get('entity_id', 'N/A')}")
                print(f"   Timestamp: {fields.get('timestamp', 'N/A')}")
                
                # Parse and display data
                if 'data' in fields:
                    try:
                        data = json.loads(fields['data']) if isinstance(fields['data'], str) else fields['data']
                        print(f"   Deal Data:")
                        print(f"      ID: {data.get('ID', data.get('id', 'N/A'))}")
                        print(f"      Title: {data.get('TITLE', data.get('title', 'N/A'))}")
                        print(f"      Stage ID: {data.get('STAGE_ID', data.get('stage_id', 'N/A'))}")
                        print(f"      Old Stage ID: {data.get('OLD_STAGE_ID', data.get('old_stage_id', 'N/A'))}")
                        print(f"      Category ID: {data.get('CATEGORY_ID', data.get('category_id', 'N/A'))}")
                        if 'OPPORTUNITY' in data or 'opportunity' in data:
                            print(f"      Opportunity: {data.get('OPPORTUNITY', data.get('opportunity', 'N/A'))}")
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"   Data (raw): {fields['data'][:200]}...")
        else:
            print(f"\n⚠️  No webhook messages found for deal 65")
            print(f"   Showing recent webhook messages for context:")
            for msg_id, fields in messages[-5:]:
                print(f"\n   Message ID: {msg_id}")
                print(f"      Event: {fields.get('event_type', 'N/A')}")
                print(f"      Entity: {fields.get('entity_type', 'N/A')} {fields.get('entity_id', 'N/A')}")
        
        return relevant_messages
        
    except Exception as e:
        print(f"\n❌ Error checking Redis stream: {e}")
        import traceback
        traceback.print_exc()
        return []

def check_file_logs():
    """Check local log files for webhook entries"""
    print("\n" + "=" * 80)
    print("CHECKING LOCAL LOG FILES FOR DEAL 65 WEBHOOKS")
    print("=" * 80)
    
    log_files = ['server.log', 'debug.log']
    relevant_entries = []
    
    for log_file in log_files:
        log_path = Path(log_file)
        if not log_path.exists():
            print(f"\n⚠️  Log file not found: {log_file}")
            continue
        
        print(f"\n📄 Checking {log_file}...")
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            print(f"   Total lines: {len(lines)}")
            
            # Search for relevant entries
            for i, line in enumerate(lines, 1):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in [
                    'deal.*65', 'entity_id.*65', 'deal 65',
                    'order.*41', 'order 41',
                    'webhook.*65', 'webhook.*41'
                ]):
                    if '65' in line and ('deal' in line_lower or 'entity_id' in line_lower or 'webhook' in line_lower):
                        relevant_entries.append((log_file, i, line.strip()))
                    elif '41' in line and ('order' in line_lower or 'webhook' in line_lower):
                        relevant_entries.append((log_file, i, line.strip()))
            
        except Exception as e:
            print(f"   ❌ Error reading {log_file}: {e}")
    
    if relevant_entries:
        print(f"\n✅ Found {len(relevant_entries)} relevant log entries:")
        for log_file, line_num, line in relevant_entries[-20:]:
            print(f"   {log_file}:{line_num}: {line[:150]}")
    else:
        print(f"\n⚠️  No relevant entries found in local log files")
    
    return relevant_entries

async def main():
    """Main function to check all log sources"""
    print("=" * 80)
    print("CHECKING LOGS FOR ORDER 41 (DEAL 65) WEBHOOK CHANGES FROM BITRIX")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Check Docker logs
    docker_entries = check_docker_logs()
    
    # Check Redis stream
    redis_messages = await check_redis_webhooks()
    
    # Check file logs
    file_entries = check_file_logs()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Docker log entries: {len(docker_entries)}")
    print(f"Redis webhook messages: {len(redis_messages)}")
    print(f"File log entries: {len(file_entries)}")
    
    if docker_entries or redis_messages or file_entries:
        print(f"\n✅ Found evidence of webhook activity for deal 65 / order 41")
    else:
        print(f"\n⚠️  No webhook activity found for deal 65 / order 41")
        print(f"   Possible reasons:")
        print(f"   - Webhook was not sent from Bitrix")
        print(f"   - Webhook was sent but not received")
        print(f"   - Logs were rotated/cleared")
        print(f"   - Different deal ID or order ID")
    
    # Write results to file
    output_file = "order_41_webhook_logs_check.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("ORDER 41 (DEAL 65) WEBHOOK LOGS CHECK\n")
        f.write("=" * 80 + "\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
        f.write(f"Docker entries: {len(docker_entries)}\n")
        f.write(f"Redis messages: {len(redis_messages)}\n")
        f.write(f"File entries: {len(file_entries)}\n")
    
    print(f"\n📝 Results written to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())


