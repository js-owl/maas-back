"""Check for recent webhook activity in Docker logs"""
import subprocess
from datetime import datetime, timedelta

def check_recent_logs():
    """Check Docker logs for recent webhook activity"""
    print("=" * 80)
    print("CHECKING RECENT WEBHOOK ACTIVITY")
    print("=" * 80)
    print(f"Time: {datetime.now().isoformat()}")
    
    try:
        # Get logs from last 10 minutes
        result = subprocess.run(
            ["docker", "logs", "backend", "--since", "10m"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30
        )
        
        logs = result.stdout
        lines = logs.split('\n')
        
        print(f"\nTotal log lines in last 10 minutes: {len(lines)}")
        
        # Find webhook-related entries
        webhook_entries = []
        test_endpoint_entries = []
        deal_entries = []
        
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            
            if 'bitrix/webhook' in line_lower or 'webhook' in line_lower:
                if 'test' in line_lower:
                    test_endpoint_entries.append((i, line.strip()))
                else:
                    webhook_entries.append((i, line.strip()))
            
            if 'deal' in line_lower and ('65' in line or '41' in line or 'stage' in line_lower):
                deal_entries.append((i, line.strip()))
        
        print(f"\n📊 Summary:")
        print(f"   Webhook entries: {len(webhook_entries)}")
        print(f"   Test endpoint entries: {len(test_endpoint_entries)}")
        print(f"   Deal-related entries: {len(deal_entries)}")
        
        if test_endpoint_entries:
            print(f"\n✅ Test Endpoint Activity ({len(test_endpoint_entries)} entries):")
            for line_num, line in test_endpoint_entries[-20:]:
                print(f"   Line {line_num}: {line[:200]}")
        
        if webhook_entries:
            print(f"\n📨 Webhook Activity ({len(webhook_entries)} entries):")
            for line_num, line in webhook_entries[-20:]:
                print(f"   Line {line_num}: {line[:200]}")
        
        if deal_entries:
            print(f"\n📋 Deal Activity ({len(deal_entries)} entries):")
            for line_num, line in deal_entries[-20:]:
                print(f"   Line {line_num}: {line[:200]}")
        
        if not test_endpoint_entries and not webhook_entries:
            print(f"\n⚠️  No webhook activity found in last 10 minutes")
            print(f"   This could mean:")
            print(f"   - Bitrix hasn't sent webhooks yet")
            print(f"   - Webhook URL in Bitrix is not configured correctly")
            print(f"   - Webhooks are being sent to a different endpoint")
        
        # Check for any POST requests
        post_requests = []
        for i, line in enumerate(lines, 1):
            if 'POST' in line and ('bitrix' in line.lower() or 'webhook' in line.lower()):
                post_requests.append((i, line.strip()))
        
        if post_requests:
            print(f"\n📤 POST Requests ({len(post_requests)} found):")
            for line_num, line in post_requests[-10:]:
                print(f"   Line {line_num}: {line[:200]}")
        
        # Write to file
        output_file = "recent_webhook_activity_check.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("RECENT WEBHOOK ACTIVITY CHECK\n")
            f.write("=" * 80 + "\n")
            f.write(f"Time: {datetime.now().isoformat()}\n\n")
            f.write(f"Webhook entries: {len(webhook_entries)}\n")
            f.write(f"Test endpoint entries: {len(test_endpoint_entries)}\n")
            f.write(f"Deal entries: {len(deal_entries)}\n\n")
            
            if test_endpoint_entries:
                f.write("\nTest Endpoint Activity:\n")
                for line_num, line in test_endpoint_entries:
                    f.write(f"Line {line_num}: {line}\n")
            
            if webhook_entries:
                f.write("\nWebhook Activity:\n")
                for line_num, line in webhook_entries:
                    f.write(f"Line {line_num}: {line}\n")
        
        print(f"\n📝 Results written to: {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_recent_logs()


