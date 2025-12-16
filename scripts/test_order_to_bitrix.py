"""
Test script to create an order and verify Bitrix deal creation
"""
import asyncio
import httpx
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8001"

async def test_order_to_bitrix():
    """Create an order and monitor Bitrix deal creation"""
    
    print("=" * 60)
    print("Testing Order Creation → Bitrix Deal Flow")
    print("=" * 60)
    
    # Step 1: Login to get auth token
    print("\n[1/5] Authenticating...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try to login with documented credentials
        # Default from database.py: username="admin", password="admin" (or ADMIN_DEFAULT_PASSWORD env var)
        # Documented in api_reference_v3.md: username="admin", password="WQu^^^kLNrDDEXBJ#WJT9Z"
        credentials_to_try = [
            {"username": "admin", "password": "admin"},  # Default from seed_admin()
            {"username": "admin", "password": "WQu^^^kLNrDDEXBJ#WJT9Z"},  # Documented password
        ]
        
        token = None
        for login_data in credentials_to_try:
        
            try:
                # Login endpoint expects JSON
                response = await client.post(
                    f"{BASE_URL}/login",
                    json=login_data
                )
                if response.status_code == 200:
                    auth_data = response.json()
                    token = auth_data.get("access_token")
                    print(f"  ✅ Authenticated successfully with username: {login_data['username']}")
                    break
                elif response.status_code == 401:
                    # Wrong password, try next
                    continue
                else:
                    print(f"  ⚠️  Login failed: {response.status_code}")
                    print(f"     Response: {response.text}")
            except Exception as e:
                print(f"  ⚠️  Login error: {e}")
                continue
        
        if not token:
            print(f"\n  ⚠️  Could not authenticate with any credentials")
            print(f"     Tried: admin/admin and admin/WQu^^^kLNrDDEXBJ#WJT9Z")
            print(f"\n  💡 You can:")
            print(f"     1. Create an order manually via frontend/API")
            print(f"     2. Check ADMIN_DEFAULT_PASSWORD env var")
            print(f"     3. Use the monitoring commands below to watch the flow")
            print(f"\n  📊 Proceeding with monitoring only...")
        
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        # Step 2: Check Redis stream before
        print("\n[2/5] Checking Redis streams (before order creation)...")
        import subprocess
        try:
            result = subprocess.run(
                ["docker", "exec", "redis", "redis-cli", "XINFO", "STREAM", "bitrix:operations"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "length: 0" in result.stdout or "length:0" in result.stdout:
                print("  ✅ Redis stream is empty (no pending operations)")
            else:
                print(f"  📊 Redis stream info:\n{result.stdout}")
        except Exception as e:
            print(f"  ⚠️  Could not check Redis: {e}")
        
        # Step 3: Create order (if authenticated)
        if not token:
            print("\n[3/5] Skipping order creation (not authenticated)")
            print("  💡 Please create an order manually, then we'll monitor the flow")
            order_id = None
        else:
            print("\n[3/5] Creating order...")
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
                "n_dimensions": 1,
                "document_ids": []
            }
            
            try:
                response = await client.post(
                    f"{BASE_URL}/orders",
                    json=order_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    order = response.json()
                    order_id = order.get("order_id")
                    print(f"  ✅ Order created successfully!")
                    print(f"     Order ID: {order_id}")
                    print(f"     Service: {order.get('service_id')}")
                    print(f"     Status: {order.get('status')}")
                    print(f"     Total Price: {order.get('total_price')}")
                elif response.status_code == 502:
                    print(f"  ⚠️  Order creation failed - calculator service unavailable")
                    print(f"     This is expected if calculator service is down")
                    order_id = None
                else:
                    print(f"  ❌ Order creation failed: {response.status_code}")
                    print(f"     Response: {response.text[:200]}")
                    order_id = None
                    
            except Exception as e:
                print(f"  ❌ Error creating order: {e}")
                order_id = None
        
        # Step 4: Wait a moment for queue processing
        print("\n[4/5] Waiting for queue processing (5 seconds)...")
        await asyncio.sleep(5)
        
        # Step 5: Check Redis stream and logs
        print("\n[5/5] Checking results...")
        
        # Check Redis stream
        try:
            result = subprocess.run(
                ["docker", "exec", "redis", "redis-cli", "XREAD", "STREAMS", "bitrix:operations", "0", "COUNT", "5"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                print("  ✅ Messages found in Redis stream:")
                print(f"     {result.stdout[:500]}")
            else:
                print("  ⚠️  No messages in Redis stream (may have been processed already)")
        except Exception as e:
            print(f"  ⚠️  Could not check Redis stream: {e}")
        
        # Check backend logs
        try:
            result = subprocess.run(
                ["docker", "logs", "backend", "--tail", "30"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logs = result.stdout
                if "QUEUE_DEAL" in logs or "Published" in logs or "Processing" in logs:
                    print("\n  ✅ Bitrix sync activity found in logs:")
                    relevant_lines = [line for line in logs.split('\n') 
                                    if any(keyword in line for keyword in 
                                          ['QUEUE_DEAL', 'Published', 'Processing', 'Bitrix deal', 'deal creation'])]
                    for line in relevant_lines[-5:]:  # Last 5 relevant lines
                        if line.strip():
                            print(f"     {line.strip()}")
                else:
                    print("\n  ⚠️  No Bitrix sync activity in recent logs")
                    print("     Check if BITRIX_WEBHOOK_URL is configured")
        except Exception as e:
            print(f"  ⚠️  Could not check logs: {e}")
        
        # Check if order has bitrix_deal_id (if we have order_id and token)
        if order_id and token:
            print("\n[Bonus] Checking if order has Bitrix deal ID...")
            try:
                response = await client.get(
                    f"{BASE_URL}/orders/{order_id}",
                    headers=headers
                )
                if response.status_code == 200:
                    order = response.json()
                    deal_id = order.get("bitrix_deal_id")
                    if deal_id:
                        print(f"  ✅ Order has Bitrix deal ID: {deal_id}")
                        print(f"     Deal should be visible in Bitrix24!")
                    else:
                        print(f"  ⏳ Order does not have Bitrix deal ID yet")
                        print(f"     This may take a few moments if worker is processing")
                else:
                    print(f"  ⚠️  Could not retrieve order details: {response.status_code}")
            except Exception as e:
                print(f"  ⚠️  Error checking order: {e}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Check Bitrix24 CRM for the new deal")
    print("2. Monitor logs: docker logs -f backend")
    print("3. Check Redis: docker exec redis redis-cli XREAD STREAMS bitrix:operations 0")


if __name__ == "__main__":
    asyncio.run(test_order_to_bitrix())

