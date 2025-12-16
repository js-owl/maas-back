"""Check all webhook activity from Docker logs"""
import subprocess
import re
from datetime import datetime
from collections import defaultdict

def check_docker_logs():
    """Extract all webhook-related entries from Docker logs"""
    print("=" * 80)
    print("CHECKING ALL WEBHOOK ACTIVITY FROM DOCKER LOGS")
    print("=" * 80)
    
    try:
        # Get all logs
        result = subprocess.run(
            ["docker", "logs", "backend"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"Error getting Docker logs: {result.stderr}")
            return
        
        logs = result.stdout
        lines = logs.split('\n')
        
        # Find all webhook-related entries
        webhook_entries = []
        error_entries = []
        successful_webhooks = []
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Webhook endpoint calls
            if '/bitrix/webhook' in line_lower or 'bitrix/webhook' in line_lower:
                webhook_entries.append((i, line.strip()))
            
            # Webhook processing errors
            if 'missing entity_id' in line_lower or 'invalid json' in line_lower:
                error_entries.append((i, line.strip()))
            
            # Successful webhook processing
            if 'bitrix webhook received' in line_lower or 'published webhook' in line_lower:
                successful_webhooks.append((i, line.strip()))
        
        print(f"\n📊 Summary:")
        print(f"   Total webhook endpoint calls: {len(webhook_entries)}")
        print(f"   Webhook processing errors: {len(error_entries)}")
        print(f"   Successful webhook processing: {len(successful_webhooks)}")
        
        # Show all webhook endpoint calls
        if webhook_entries:
            print(f"\n📨 All Webhook Endpoint Calls:")
            for line_num, line in webhook_entries:
                # Extract timestamp if available
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})', line)
                timestamp = timestamp_match.group(1) if timestamp_match else "N/A"
                
                # Extract status code
                status_match = re.search(r'(\d{3})\s+(OK|Bad Request|Internal Server Error)', line)
                status = status_match.group(1) if status_match else "N/A"
                
                # Extract IP and query params
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+):\d+', line)
                ip = ip_match.group(1) if ip_match else "N/A"
                
                query_match = re.search(r'Query:\s*([^,]+)', line)
                query = query_match.group(1) if query_match else ""
                
                print(f"\n   Line {line_num}:")
                print(f"      Timestamp: {timestamp}")
                print(f"      IP: {ip}")
                print(f"      Status: {status}")
                if query:
                    print(f"      Query: {query}")
                print(f"      Full line: {line[:200]}")
        
        # Show errors
        if error_entries:
            print(f"\n❌ Webhook Processing Errors:")
            for line_num, line in error_entries:
                print(f"   Line {line_num}: {line}")
        
        # Show successful webhooks
        if successful_webhooks:
            print(f"\n✅ Successful Webhook Processing:")
            for line_num, line in successful_webhooks:
                # Extract deal/entity info
                deal_match = re.search(r'deal\s+(\d+)', line, re.IGNORECASE)
                entity_match = re.search(r'entity_id[:\s]+(\d+)', line, re.IGNORECASE)
                deal_id = deal_match.group(1) if deal_match else (entity_match.group(1) if entity_match else "N/A")
                
                print(f"\n   Line {line_num}:")
                print(f"      Deal/Entity ID: {deal_id}")
                print(f"      Full line: {line[:200]}")
                
                # Check if this is deal 65
                if deal_id == "65":
                    print(f"      ⭐ THIS IS DEAL 65!")
        else:
            print(f"\n⚠️  No successful webhook processing found in logs")
            print(f"   This could mean:")
            print(f"   - All webhooks failed validation (missing entity_id)")
            print(f"   - Webhooks were processed but logs were rotated")
            print(f"   - Webhook processing logs are at DEBUG level")
        
        # Search for deal 65 specifically
        print(f"\n🔍 Searching for Deal 65 specifically...")
        deal_65_entries = []
        for i, line in enumerate(lines):
            # Look for deal 65, entity_id 65, or order 41
            if re.search(r'\b65\b', line) and ('deal' in line.lower() or 'entity' in line.lower() or 'webhook' in line.lower()):
                # Exclude false positives like "0.65ms"
                if not re.search(r'0\.65|\.65ms|65ms', line):
                    deal_65_entries.append((i, line.strip()))
        
        if deal_65_entries:
            print(f"   Found {len(deal_65_entries)} potential deal 65 entries:")
            for line_num, line in deal_65_entries[:20]:  # Show first 20
                print(f"      Line {line_num}: {line[:150]}")
        else:
            print(f"   ⚠️  No deal 65 entries found in logs")
        
        # Write results to file
        output_file = "all_webhook_activity_check.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("ALL WEBHOOK ACTIVITY CHECK\n")
            f.write("=" * 80 + "\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
            f.write(f"Total webhook calls: {len(webhook_entries)}\n")
            f.write(f"Errors: {len(error_entries)}\n")
            f.write(f"Successful: {len(successful_webhooks)}\n\n")
            
            if webhook_entries:
                f.write("\nAll Webhook Calls:\n")
                for line_num, line in webhook_entries:
                    f.write(f"Line {line_num}: {line}\n")
            
            if error_entries:
                f.write("\nErrors:\n")
                for line_num, line in error_entries:
                    f.write(f"Line {line_num}: {line}\n")
            
            if successful_webhooks:
                f.write("\nSuccessful Webhooks:\n")
                for line_num, line in successful_webhooks:
                    f.write(f"Line {line_num}: {line}\n")
        
        print(f"\n📝 Full results written to: {output_file}")
        
    except FileNotFoundError:
        print("Docker command not found")
    except subprocess.TimeoutExpired:
        print("Timeout getting Docker logs")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_docker_logs()

