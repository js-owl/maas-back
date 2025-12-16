"""Test Bitrix API calls directly to see error messages"""
import asyncio
import sys
sys.path.insert(0, '/app')

from backend.bitrix.client import bitrix_client

async def test():
    print("=" * 60)
    print("Testing Bitrix API Calls Directly")
    print("=" * 60)
    
    print(f"\n1. Configuration:")
    print(f"   - Base URL: {bitrix_client.base_url}")
    print(f"   - Configured: {bitrix_client.is_configured()}")
    
    print(f"\n2. Testing crm.dealcategory.list:")
    try:
        resp = await bitrix_client._post("crm.dealcategory.list", {})
        print(f"   Response type: {type(resp)}")
        if resp:
            print(f"   Response keys: {resp.keys() if isinstance(resp, dict) else 'Not a dict'}")
            if isinstance(resp, dict):
                if "_error" in resp:
                    error = resp["_error"]
                    print(f"   ❌ Error occurred:")
                    print(f"      Status Code: {error.get('status_code')}")
                    print(f"      Error Body: {error.get('error_body', '')[:500]}")
                    print(f"      Method: {error.get('method')}")
                elif "result" in resp:
                    result = resp["result"]
                    print(f"   ✅ Success: {len(result) if isinstance(result, list) else 'Not a list'} categories")
                    if isinstance(result, list):
                        for cat in result[:3]:
                            print(f"      - {cat}")
                else:
                    print(f"   Response: {resp}")
            else:
                print(f"   Response: {resp}")
        else:
            print("   ❌ Response is None")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n3. Testing crm.dealcategory.add:")
    try:
        payload = {
            "FIELDS[NAME]": "MaaS Test",
            "FIELDS[STAGES][0][NAME]": "New Order",
            "FIELDS[STAGES][0][SORT]": "10",
            "FIELDS[STAGES][0][SEMANTICS]": "P"
        }
        resp = await bitrix_client._post("crm.dealcategory.add", payload)
        print(f"   Response type: {type(resp)}")
        if resp:
            if isinstance(resp, dict):
                if "_error" in resp:
                    error = resp["_error"]
                    print(f"   ❌ Error occurred:")
                    print(f"      Status Code: {error.get('status_code')}")
                    print(f"      Error Body: {error.get('error_body', '')[:500]}")
                    print(f"      Method: {error.get('method')}")
                elif "result" in resp:
                    print(f"   ✅ Success: Category ID = {resp['result']}")
                else:
                    print(f"   Response: {resp}")
            else:
                print(f"   Response: {resp}")
        else:
            print("   ❌ Response is None")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test())







