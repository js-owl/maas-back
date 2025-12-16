"""
Test script to create an order and verify MaaS funnel integration
"""
import asyncio
import httpx
import json

# Configuration
BASE_URL = "http://localhost:8001"  # Local Docker runs on port 8001
TEST_USERNAME = "admin"  # From .env: ADMIN_USERNAME
# Try both passwords - default and new
TEST_PASSWORDS = ["admin", "WQu^^^kLNrDDEXBJ#WJT9Z"]  # From .env: ADMIN_DEFAULT_PASSWORD and ADMIN_NEW_PASSWORD

async def test_create_order():
    """Test order creation and verify Bitrix deal creation"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 60)
        print("Testing Order Creation with MaaS Funnel Integration")
        print("=" * 60)
        
        # Step 1: Login - try both passwords
        print("\n[1/4] Logging in...")
        access_token = None
        for password in TEST_PASSWORDS:
            login_response = await client.post(
                f"{BASE_URL}/login",
                json={
                    "username": TEST_USERNAME,
                    "password": password
                }
            )
            
            if login_response.status_code == 200:
                token_data = login_response.json()
                access_token = token_data.get("access_token")
                if access_token:
                    print(f"✅ Logged in successfully with password: {'default' if password == TEST_PASSWORDS[0] else 'new'}")
                    break
        
        if not access_token:
            print(f"❌ Login failed with both passwords")
            print(f"Tried username: {TEST_USERNAME}")
            return
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Step 2: Create order
        print("\n[2/4] Creating order...")
        order_data = {
            "service_id": "cnc-milling",
            "quantity": 1,
            "length": 100,
            "width": 50,
            "height": 25,
            "material_id": "alum_D16",
            "material_form": "rod",
            "tolerance_id": "1",
            "finish_id": "1",
            "cover_id": ["1"],
            "k_otk": "1",
            "k_cert": ["a", "f"],
            "n_dimensions": 3
        }
        
        order_response = await client.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers=headers
        )
        
        if order_response.status_code != 200:
            print(f"❌ Order creation failed: {order_response.status_code}")
            print(f"Response: {order_response.text}")
            return
        
        order = order_response.json()
        order_id = order.get("order_id")
        print(f"✅ Order created successfully: Order ID {order_id}")
        print(f"   Status: {order.get('status')}")
        print(f"   Total Price: {order.get('total_price')}")
        print(f"   Bitrix Deal ID: {order.get('bitrix_deal_id', 'Not yet created')}")
        
        # Step 3: Wait a bit for worker to process
        print("\n[3/4] Waiting for Bitrix worker to process (10 seconds)...")
        await asyncio.sleep(10)
        
        # Step 4: Check order again to see if deal was created
        print("\n[4/4] Checking order status...")
        order_check = await client.get(
            f"{BASE_URL}/orders/{order_id}",
            headers=headers
        )
        
        if order_check.status_code == 200:
            updated_order = order_check.json()
            bitrix_deal_id = updated_order.get("bitrix_deal_id")
            
            if bitrix_deal_id:
                print(f"✅ Bitrix deal created: Deal ID {bitrix_deal_id}")
                print(f"   Order status: {updated_order.get('status')}")
                print("\n" + "=" * 60)
                print("SUCCESS: Order and Bitrix deal created!")
                print("=" * 60)
                print("\nNext steps:")
                print("1. Check Bitrix CRM for the new deal in 'MaaS' funnel")
                print("2. Verify the deal is in 'New Order' stage (mapped from 'pending')")
                print("3. Check backend logs for funnel initialization and deal creation")
            else:
                print("⚠️  Bitrix deal not yet created")
                print("   This might be normal if the worker hasn't processed it yet")
                print("   Check backend logs and Redis stream for processing status")
        else:
            print(f"❌ Failed to check order: {order_check.status_code}")
        
        print("\n" + "=" * 60)
        print("Test completed!")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_create_order())

