"""Check logs for webhook activity with test parameter"""
import re
from pathlib import Path
from datetime import datetime

def check_webhook_logs():
    """Check server.log for webhook requests with test parameter"""
    print("=" * 80)
    print("CHECKING WEBHOOK LOGS FOR TEST PARAMETER")
    print("=" * 80)
    
    log_file = Path("server.log")
    
    if not log_file.exists():
        print(f"\n❌ Log file not found: {log_file}")
        print(f"   Current directory: {Path.cwd()}")
        return
    
    print(f"\n📄 Reading log file: {log_file}")
    print(f"   File size: {log_file.stat().st_size} bytes")
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        print(f"   Total lines: {len(lines)}")
        
        # Search for webhook-related entries
        webhook_entries = []
        test_entries = []
        bitrix_webhook_entries = []
        
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            
            # Check for webhook mentions
            if 'webhook' in line_lower:
                webhook_entries.append((i, line.strip()))
            
            # Check for test parameter
            if 'test' in line_lower and ('test2' in line_lower or 'test=' in line_lower):
                test_entries.append((i, line.strip()))
            
            # Check for bitrix/webhook path
            if 'bitrix/webhook' in line_lower or '/bitrix/webhook' in line_lower:
                bitrix_webhook_entries.append((i, line.strip()))
        
        # Display results
        print(f"\n📊 Search Results:")
        print(f"   Webhook mentions: {len(webhook_entries)}")
        print(f"   Test parameter mentions: {len(test_entries)}")
        print(f"   /bitrix/webhook path mentions: {len(bitrix_webhook_entries)}")
        
        if webhook_entries:
            print(f"\n🔍 Webhook-related entries:")
            for line_num, line in webhook_entries[-10:]:  # Show last 10
                print(f"   Line {line_num}: {line[:100]}...")
        
        if test_entries:
            print(f"\n🔍 Test parameter entries:")
            for line_num, line in test_entries:
                print(f"   Line {line_num}: {line[:100]}...")
        
        if bitrix_webhook_entries:
            print(f"\n🔍 /bitrix/webhook endpoint entries:")
            for line_num, line in bitrix_webhook_entries:
                print(f"   Line {line_num}: {line[:100]}...")
        
        # Check for incoming request entries
        print(f"\n🔍 Checking for incoming request entries with /bitrix/webhook...")
        request_entries = []
        for i, line in enumerate(lines, 1):
            if 'incoming request' in line.lower() and 'bitrix/webhook' in line.lower():
                request_entries.append((i, line.strip()))
        
        if request_entries:
            print(f"   Found {len(request_entries)} request(s) to /bitrix/webhook:")
            for line_num, line in request_entries:
                print(f"   Line {line_num}: {line}")
                
                # Extract query parameters
                if 'query' in line.lower():
                    query_match = re.search(r'Query:\s*([^,]+)', line, re.IGNORECASE)
                    if query_match:
                        query_str = query_match.group(1)
                        print(f"      Query parameters: {query_str}")
                        if 'test' in query_str.lower():
                            print(f"      ✅ Found 'test' parameter in query!")
        else:
            print(f"   ℹ️  No incoming request entries found for /bitrix/webhook")
        
        # Summary
        print(f"\n" + "=" * 80)
        print(f"SUMMARY")
        print(f"=" * 80)
        
        if bitrix_webhook_entries or request_entries:
            print(f"✅ Webhook endpoint was accessed")
            if test_entries or any('test' in line.lower() for _, line in request_entries):
                print(f"✅ Test parameter was found in logs")
            else:
                print(f"⚠️  Test parameter not found in logs (may be in different format)")
        else:
            print(f"❌ No webhook endpoint access found in logs")
            print(f"   This could mean:")
            print(f"   - Webhook was not received")
            print(f"   - Logs were rotated/cleared")
            print(f"   - Different log file location")
            print(f"   - Server was not running when webhook was sent")
        
        # Check recent entries
        print(f"\n📅 Recent log entries (last 5 lines):")
        for line in lines[-5:]:
            print(f"   {line.strip()}")
            
    except Exception as e:
        print(f"\n❌ Error reading log file: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    output = []
    
    # Capture print output
    class OutputCapture:
        def write(self, text):
            output.append(text)
            sys.stdout.write(text)
    
    sys.stdout = OutputCapture()
    
    check_webhook_logs()
    
    # Write to file
    with open("webhook_logs_check_result.txt", "w", encoding="utf-8") as f:
        f.write("".join(output))
