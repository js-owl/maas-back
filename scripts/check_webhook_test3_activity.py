"""Check for webhook activity with test3 parameter"""
import subprocess
from datetime import datetime

def check_webhook_activity():
    """Check Docker logs for webhook activity with test3"""
    print("=" * 80)
    print("CHECKING FOR WEBHOOK ACTIVITY WITH TEST3 PARAMETER")
    print("=" * 80)
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Expected URL: http://192.168.137.1:8001/bitrix/webhook/test?test=\"test3\"&entity_id={{ID}}")
    print()
    
    try:
        # Get recent logs (last 10 minutes)
        result = subprocess.run(
            ["docker", "logs", "backend", "--since", "10m"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30
        )
        
        logs = result.stdout
        lines = logs.split('\n')
        
        print(f"Total log lines in last 10 minutes: {len(lines)}")
        
        # Find webhook test endpoint activity
        test_endpoint_requests = []
        test3_requests = []
        entity_id_requests = []
        bitrix_webhook_test_blocks = []
        
        in_test_block = False
        current_block = []
        
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            
            # Check for test endpoint requests
            if '/bitrix/webhook/test' in line_lower:
                test_endpoint_requests.append((i, line.strip()))
            
            # Check for test3 parameter
            if 'test3' in line_lower or 'test="test3"' in line or "test='test3'" in line:
                test3_requests.append((i, line.strip()))
            
            # Check for entity_id parameter
            if 'entity_id' in line_lower:
                entity_id_requests.append((i, line.strip()))
            
            # Capture full test endpoint log blocks
            if 'BITRIX WEBHOOK TEST ENDPOINT' in line:
                in_test_block = True
                current_block = [line.strip()]
            elif in_test_block:
                current_block.append(line.strip())
                if '=' * 80 in line or (len(current_block) > 30):
                    bitrix_webhook_test_blocks.append((i, '\n'.join(current_block)))
                    current_block = []
                    in_test_block = False
        
        # If we're still in a block, save it
        if in_test_block and current_block:
            bitrix_webhook_test_blocks.append((len(lines), '\n'.join(current_block)))
        
        print(f"\n📊 Summary:")
        print(f"   Test endpoint requests: {len(test_endpoint_requests)}")
        print(f"   Requests with test3: {len(test3_requests)}")
        print(f"   Requests with entity_id: {len(entity_id_requests)}")
        print(f"   Full test endpoint log blocks: {len(bitrix_webhook_test_blocks)}")
        
        if test_endpoint_requests:
            print(f"\n📨 Test Endpoint Requests ({len(test_endpoint_requests)} found):")
            for line_num, line in test_endpoint_requests[-20:]:
                print(f"   Line {line_num}: {line[:200]}")
        
        if test3_requests:
            print(f"\n✅ Requests with test3 parameter ({len(test3_requests)} found):")
            for line_num, line in test3_requests:
                print(f"   Line {line_num}: {line[:200]}")
        else:
            print(f"\n⚠️  No requests found with test3 parameter")
        
        if entity_id_requests:
            print(f"\n📋 Requests with entity_id parameter ({len(entity_id_requests)} found):")
            for line_num, line in entity_id_requests[-10:]:
                print(f"   Line {line_num}: {line[:200]}")
        
        if bitrix_webhook_test_blocks:
            print(f"\n🔍 Full Test Endpoint Log Blocks ({len(bitrix_webhook_test_blocks)} found):")
            for block_num, (line_num, block) in enumerate(bitrix_webhook_test_blocks[-5:], 1):
                print(f"\n   Block {block_num} (starting at line {line_num}):")
                print("   " + "=" * 76)
                # Show first 50 lines of each block
                block_lines = block.split('\n')
                for block_line in block_lines[:50]:
                    print(f"   {block_line[:200]}")
                if len(block_lines) > 50:
                    print(f"   ... ({len(block_lines) - 50} more lines)")
                print("   " + "=" * 76)
        else:
            print(f"\n⚠️  No full test endpoint log blocks found")
            print(f"   This means no requests reached the test endpoint")
        
        # Check for any POST requests from external IPs
        external_requests = []
        for i, line in enumerate(lines, 1):
            if 'POST' in line and 'bitrix/webhook' in line.lower():
                # Check if it's from external IP (not 127.0.0.1 or 172.21.0.1)
                if '127.0.0.1' not in line and '172.21.0.1' not in line:
                    external_requests.append((i, line.strip()))
        
        if external_requests:
            print(f"\n🌐 External Requests (not localhost/Docker):")
            for line_num, line in external_requests:
                print(f"   Line {line_num}: {line[:200]}")
        else:
            print(f"\n⚠️  No external requests found (all from localhost/Docker)")
        
        # Write results to file
        output_file = "webhook_test3_activity_check.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("WEBHOOK TEST3 ACTIVITY CHECK\n")
            f.write("=" * 80 + "\n")
            f.write(f"Time: {datetime.now().isoformat()}\n\n")
            f.write(f"Test endpoint requests: {len(test_endpoint_requests)}\n")
            f.write(f"Requests with test3: {len(test3_requests)}\n")
            f.write(f"Requests with entity_id: {len(entity_id_requests)}\n\n")
            
            if test_endpoint_requests:
                f.write("\nTest Endpoint Requests:\n")
                for line_num, line in test_endpoint_requests:
                    f.write(f"Line {line_num}: {line}\n")
            
            if test3_requests:
                f.write("\nRequests with test3:\n")
                for line_num, line in test3_requests:
                    f.write(f"Line {line_num}: {line}\n")
            
            if bitrix_webhook_test_blocks:
                f.write("\nFull Test Endpoint Log Blocks:\n")
                for line_num, block in bitrix_webhook_test_blocks:
                    f.write(f"\nBlock starting at line {line_num}:\n")
                    f.write(block)
                    f.write("\n" + "=" * 80 + "\n")
        
        print(f"\n📝 Results written to: {output_file}")
        
        # Final summary
        print(f"\n" + "=" * 80)
        if test3_requests or bitrix_webhook_test_blocks:
            print("✅ WEBHOOK REQUESTS RECEIVED!")
            print("   Check the detailed log blocks above to see the full request format.")
        else:
            print("❌ NO WEBHOOK REQUESTS RECEIVED YET")
            print("   Possible reasons:")
            print("   - Bitrix hasn't sent webhooks yet (may have delay)")
            print("   - Webhook URL in Bitrix might be incorrect")
            print("   - Network/firewall blocking requests")
            print("   - Bitrix webhook might not be active")
        print("=" * 80)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_webhook_activity()


