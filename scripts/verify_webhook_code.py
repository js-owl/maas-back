"""Verify the webhook code is correct"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Read the actual file
with open('backend/bitrix/webhook_router.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check for token verification
if 'return True' in content and 'Token verification disabled' in content:
    # Find the function
    if 'def verify_bitrix_webhook_token' in content:
        start = content.find('def verify_bitrix_webhook_token')
        func_content = content[start:start+200]
        
        if 'return True' in func_content and 'Token verification disabled' in func_content:
            print("✅ Code is correct - token verification is disabled")
            print("\nFunction snippet:")
            lines = func_content.split('\n')[:10]
            for line in lines:
                print(f"  {line}")
        else:
            print("❌ Code issue - token verification might not be disabled")
    else:
        print("❌ Function not found")
else:
    print("❌ Code doesn't match expected pattern")

# Check for HTTPException 401
if 'raise HTTPException(status_code=401' in content:
    # Check if it's commented
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'raise HTTPException(status_code=401' in line:
            if line.strip().startswith('#'):
                print(f"\n✅ HTTPException 401 is commented out (line {i+1})")
            else:
                print(f"\n❌ HTTPException 401 is NOT commented out (line {i+1})")
                print(f"   {line}")





