"""Check for all POST requests to /bitrix/webhook/test endpoint"""
import subprocess
from datetime import datetime

def check_webhook_test_endpoint():
    """Check Docker logs for POST requests to /bitrix/webhook/test"""
    print("=" * 80)
    print("CHECKING FOR POST REQUESTS TO /bitrix/webhook/test ENDPOINT")
    print("=" * 80)
    print(f"Time: {datetime.now().isoformat()}")
    print()
    
    try:
        # Get all logs
        result = subprocess.run(
            ["docker", "logs", "backend"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30
        )
        
        logs = result.stdout
        lines = logs.split('\n')
        
        print(f"Total log lines: {len(lines)}")
        
        # Find all requests to /bitrix/webhook/test
        test_endpoint_requests = []
        test_endpoint_details = []
        in_test_block = False
        current_block = []
        block_start_line = 0
        
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            
            # Check for any mention of /bitrix/webhook/test
            if '/bitrix/webhook/test' in line_lower or 'bitrix/webhook/test' in line_lower:
                test_endpoint_requests.append((i, line.strip()))
            
            # Check for POST requests to test endpoint
            if 'POST' in line and '/bitrix/webhook/test' in line_lower:
                test_endpoint_requests.append((i, line.strip()))
            
            # Check for INCOMING REQUEST to test endpoint
            if 'INCOMING REQUEST' in line and '/bitrix/webhook/test' in line_lower:
                test_endpoint_requests.append((i, line.strip()))
            
            # Capture full test endpoint log blocks
            if 'BITRIX WEBHOOK TEST ENDPOINT' in line:
                in_test_block = True
                current_block = [line.strip()]
                block_start_line = i
            elif in_test_block:
                current_block.append(line.strip())
                # End of block is marked by separator line or after reasonable length
                if '=' * 80 in line or len(current_block) > 50:
                    test_endpoint_details.append({
                        'start_line': block_start_line,
                        'lines': current_block.copy()
                    })
                    current_block = []
                    in_test_block = False
        
        # If we're still in a block, save it
        if in_test_block and current_block:
            test_endpoint_details.append({
                'start_line': block_start_line,
                'lines': current_block
            })
        
        print(f"\n📊 Summary:")
        print(f"   Total mentions of /bitrix/webhook/test: {len(test_endpoint_requests)}")
        print(f"   Full test endpoint log blocks: {len(test_endpoint_details)}")
        
        if test_endpoint_requests:
            print(f"\n📨 All Requests/Mentions of /bitrix/webhook/test:")
            for line_num, line in test_endpoint_requests[-30:]:
                # Extract key info
                if 'POST' in line:
                    status_match = None
                    if '200' in line:
                        status_match = '200 OK'
                    elif '400' in line:
                        status_match = '400 Bad Request'
                    elif '500' in line:
                        status_match = '500 Internal Server Error'
                    
                    ip_match = None
                    if '127.0.0.1' in line:
                        ip_match = '127.0.0.1 (localhost)'
                    elif '172.21.0.1' in line or '172.21' in line:
                        ip_match = '172.21.0.1 (Docker internal)'
                    elif '192.168' in line:
                        ip_match = '192.168.x.x (external)'
                    
                    print(f"\n   Line {line_num}:")
                    print(f"      {line[:200]}")
                    if status_match:
                        print(f"      Status: {status_match}")
                    if ip_match:
                        print(f"      IP: {ip_match}")
                else:
                    print(f"   Line {line_num}: {line[:200]}")
        else:
            print(f"\n⚠️  No requests found to /bitrix/webhook/test endpoint")
        
        if test_endpoint_details:
            print(f"\n🔍 Full Test Endpoint Log Blocks ({len(test_endpoint_details)} found):")
            for block_num, block_info in enumerate(test_endpoint_details[-5:], 1):
                print(f"\n   Block {block_num} (starting at line {block_info['start_line']}):")
                print("   " + "=" * 76)
                for block_line in block_info['lines'][:60]:  # Show first 60 lines
                    print(f"   {block_line[:200]}")
                if len(block_info['lines']) > 60:
                    print(f"   ... ({len(block_info['lines']) - 60} more lines)")
                print("   " + "=" * 76)
        else:
            print(f"\n⚠️  No full test endpoint log blocks found")
            print(f"   This means no requests reached the test endpoint with full logging")
        
        # Check for requests from external IPs (not localhost)
        external_requests = []
        for line_num, line in test_endpoint_requests:
            if 'POST' in line and '/bitrix/webhook/test' in line.lower():
                # Check if it's from external IP
                if '127.0.0.1' not in line and '172.21.0.1' not in line and '172.21' not in line:
                    if '192.168' in line or any(char.isdigit() and line.count('.') >= 3 for char in line):
                        external_requests.append((line_num, line.strip()))
        
        if external_requests:
            print(f"\n🌐 External Requests (from Bitrix):")
            for line_num, line in external_requests:
                print(f"   Line {line_num}: {line[:200]}")
        else:
            print(f"\n⚠️  No external requests found")
            print(f"   All requests are from localhost or Docker internal network")
            print(f"   This suggests Bitrix hasn't sent webhooks yet")
        
        # Write results to file
        output_file = "webhook_test_endpoint_check.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("WEBHOOK TEST ENDPOINT CHECK\n")
            f.write("=" * 80 + "\n")
            f.write(f"Time: {datetime.now().isoformat()}\n\n")
            f.write(f"Total mentions: {len(test_endpoint_requests)}\n")
            f.write(f"Full log blocks: {len(test_endpoint_details)}\n\n")
            
            if test_endpoint_requests:
                f.write("\nAll Requests/Mentions:\n")
                for line_num, line in test_endpoint_requests:
                    f.write(f"Line {line_num}: {line}\n")
            
            if test_endpoint_details:
                f.write("\n\nFull Test Endpoint Log Blocks:\n")
                for block_info in test_endpoint_details:
                    f.write(f"\nBlock starting at line {block_info['start_line']}:\n")
                    f.write("\n".join(block_info['lines']))
                    f.write("\n" + "=" * 80 + "\n")
        
        print(f"\n📝 Results written to: {output_file}")
        
        # Final summary
        print(f"\n" + "=" * 80)
        if test_endpoint_details or external_requests:
            print("✅ WEBHOOK REQUESTS FOUND!")
            if test_endpoint_details:
                print(f"   Found {len(test_endpoint_details)} full log block(s) with request details")
            if external_requests:
                print(f"   Found {len(external_requests)} external request(s) from Bitrix")
        else:
            print("❌ NO WEBHOOK REQUESTS FROM BITRIX YET")
            print("   Only localhost/test requests found")
            print("   Bitrix webhooks have not been received")
        print("=" * 80)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_webhook_test_endpoint()


