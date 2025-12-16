"""Test simple Bitrix API call to verify webhook works"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.bitrix.client import bitrix_client

async def test():
    print("=" * 60)
    print("Testing Simple Bitrix API Call")
    print("=" * 60)
    
    print(f"\n1. Configuration:")
    print(f"   - Base URL: {bitrix_client.base_url}")
    print(f"   - Configured: {bitrix_client.is_configured()}")
    
    print(f"\n2. Testing crm.user.get (simple call):")
    try:
        resp = await bitrix_client._post("crm.user.get", {})
        if resp:
            if isinstance(resp, dict) and "_error" in resp:
                error = resp["_error"]
                print(f"   ❌ Error:")
                print(f"      Status: {error.get('status_code')}")
                print(f"      Body: {error.get('error_body', '')[:300]}")
            else:
                print(f"   ✅ Success: {resp}")
        else:
            print("   ❌ Response is None")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n3. Testing crm.deal.get (if we have a deal ID):")
    try:
        # Try with a non-existent deal ID to see if API responds
        resp = await bitrix_client._post("crm.deal.get", {"id": 999999})
        if resp:
            if isinstance(resp, dict) and "_error" in resp:
                error = resp["_error"]
                status = error.get('status_code')
                body = error.get('error_body', '')
                print(f"   Status: {status}")
                if status == 400 and "Not found" in body:
                    print(f"   ✅ API is working (expected 'not found' for non-existent deal)")
                else:
                    print(f"   Response: {body[:300]}")
            else:
                print(f"   ✅ Response: {resp}")
        else:
            print("   ❌ Response is None")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test())







