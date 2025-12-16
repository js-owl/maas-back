"""Test the webhook endpoint with test parameter"""
import requests
import json

def test_webhook():
    """Test webhook endpoint with test parameter"""
    url = "http://192.168.0.104:8001/bitrix/webhook"
    params = {"test": "test2"}
    
    print("=" * 80)
    print("TESTING WEBHOOK ENDPOINT")
    print("=" * 80)
    print(f"\nURL: {url}")
    print(f"Query parameter: test=test2")
    print(f"Method: POST")
    
    try:
        # Test with empty JSON body
        response = requests.post(
            url,
            params=params,
            json={},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"\n📊 Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Text: {response.text}")
        
        if response.status_code == 200:
            print(f"\n✅ Webhook endpoint is accessible and responded successfully!")
        elif response.status_code == 401:
            print(f"\n⚠️  Webhook endpoint requires authentication (BITRIX_WEBHOOK_TOKEN)")
            print(f"   This is expected if token is configured")
        elif response.status_code == 400:
            print(f"\n⚠️  Bad request - may need valid Bitrix webhook payload")
        else:
            print(f"\n⚠️  Unexpected status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Connection Error: Cannot reach {url}")
        print(f"   Make sure the server is running on 192.168.0.104:8001")
    except requests.exceptions.Timeout:
        print(f"\n❌ Timeout: Server did not respond in time")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_webhook()





