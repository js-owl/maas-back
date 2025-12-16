"""Check for specific POST requests to webhook endpoint with test and entity_id parameters"""
import subprocess
import re
from collections import defaultdict

def check_webhook_requests():
    """Check Docker logs for webhook POST requests with specific parameters"""
    print("=" * 80)
    print("CHECKING FOR WEBHOOK POST REQUESTS WITH TEST AND ENTITY_ID PARAMETERS")
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
        
        # Find all webhook-related requests
        webhook_requests = []
        test_entity_requests = []
        
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            
            # Check for webhook endpoint
            if '/bitrix/webhook' in line_lower or 'bitrix/webhook' in line_lower:
                # Check for POST requests
                if 'post' in line_lower or 'incoming request' in line_lower:
                    webhook_requests.append((i, line.strip()))
                    
                    # Check for test parameter
                    if 'test' in line_lower:
                        # Check for entity_id parameter
                        if 'entity_id' in line_lower or 'entity' in line_lower:
                            test_entity_requests.append((i, line.strip()))
        
        print(f"\n📊 Summary:")
        print(f"   Total webhook POST requests: {len(webhook_requests)}")
        print(f"   Requests with 'test' parameter: {len([r for r in webhook_requests if 'test' in r[1].lower()])}")
        print(f"   Requests with 'entity_id' parameter: {len([r for r in webhook_requests if 'entity_id' in r[1].lower()])}")
        print(f"   Requests with both 'test' and 'entity_id': {len(test_entity_requests)}")
        
        # Show all webhook requests
        if webhook_requests:
            print(f"\n📨 All Webhook POST Requests:")
            for line_num, line in webhook_requests:
                # Extract query parameters
                query_match = re.search(r'Query:\s*([^,]+)', line, re.IGNORECASE)
                query = query_match.group(1) if query_match else ""
                
                # Extract IP
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+):\d+', line)
                ip = ip_match.group(1) if ip_match else "N/A"
                
                # Extract status
                status_match = re.search(r'Status:\s*(\d+)', line, re.IGNORECASE)
                status = status_match.group(1) if status_match else "N/A"
                
                print(f"\n   Line {line_num}:")
                print(f"      IP: {ip}")
                print(f"      Status: {status}")
                if query:
                    print(f"      Query: {query}")
                    
                    # Check for entity_id in query
                    if 'entity_id' in query.lower():
                        entity_id_match = re.search(r'entity_id[=:]?\s*(\d+)', query, re.IGNORECASE)
                        if entity_id_match:
                            entity_id = entity_id_match.group(1)
                            print(f"      ⭐ Entity ID found: {entity_id}")
                            if entity_id == "65":
                                print(f"      ✅ THIS IS DEAL 65!")
                
                print(f"      Full line: {line[:200]}")
        
        # Show requests with test and entity_id
        if test_entity_requests:
            print(f"\n✅ Requests with 'test' and 'entity_id' parameters:")
            for line_num, line in test_entity_requests:
                print(f"\n   Line {line_num}:")
                
                # Extract entity_id
                entity_id_match = re.search(r'entity_id[=:]?\s*(\d+)', line, re.IGNORECASE)
                if entity_id_match:
                    entity_id = entity_id_match.group(1)
                    print(f"      Entity ID: {entity_id}")
                    if entity_id == "65":
                        print(f"      ⭐ THIS IS DEAL 65!")
                
                # Extract test parameter
                test_match = re.search(r'test[=:]?\s*([^&\s,]+)', line, re.IGNORECASE)
                if test_match:
                    test_val = test_match.group(1)
                    print(f"      Test parameter: {test_val}")
                
                print(f"      Full line: {line[:250]}")
        else:
            print(f"\n⚠️  No requests found with both 'test' and 'entity_id' parameters")
        
        # Search for specific pattern: test="test2"&entity_id=
        pattern_requests = []
        for i, line in enumerate(lines, 1):
            if re.search(r'test\s*=\s*["\']?test2["\']?', line, re.IGNORECASE):
                if 'entity_id' in line.lower():
                    pattern_requests.append((i, line.strip()))
        
        if pattern_requests:
            print(f"\n🔍 Requests matching pattern 'test=\"test2\"&entity_id=':")
            for line_num, line in pattern_requests:
                print(f"   Line {line_num}: {line[:250]}")
        else:
            print(f"\n⚠️  No requests found matching pattern 'test=\"test2\"&entity_id='")
        
        # Check for IP 192.168.137.1
        ip_137_requests = []
        for i, line in enumerate(lines, 1):
            if '192.168.137.1' in line and 'bitrix/webhook' in line.lower():
                ip_137_requests.append((i, line.strip()))
        
        if ip_137_requests:
            print(f"\n🌐 Requests from IP 192.168.137.1:")
            for line_num, line in ip_137_requests:
                print(f"   Line {line_num}: {line[:250]}")
        else:
            print(f"\n⚠️  No requests found from IP 192.168.137.1")
        
        # Write results to file
        output_file = "webhook_post_requests_check.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("WEBHOOK POST REQUESTS CHECK\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total webhook requests: {len(webhook_requests)}\n")
            f.write(f"Requests with test+entity_id: {len(test_entity_requests)}\n\n")
            
            if webhook_requests:
                f.write("\nAll Webhook Requests:\n")
                for line_num, line in webhook_requests:
                    f.write(f"Line {line_num}: {line}\n")
            
            if test_entity_requests:
                f.write("\nRequests with test and entity_id:\n")
                for line_num, line in test_entity_requests:
                    f.write(f"Line {line_num}: {line}\n")
        
        print(f"\n📝 Results written to: {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_webhook_requests()


