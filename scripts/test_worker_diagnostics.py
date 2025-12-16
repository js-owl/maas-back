"""
Diagnostic script to test Bitrix Redis worker integration
"""
import asyncio
import httpx
import json
import os
from datetime import datetime

import os
# Use internal URL when running in container, external when running locally
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000" if os.path.exists("/app") else "http://localhost:8001")

async def get_admin_token():
    """Get admin authentication token"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try common admin credentials
        credentials = [
            {"username": "admin", "password": "admin"},
            {"username": "admin", "password": os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123")},
        ]
        
        for creds in credentials:
            try:
                response = await client.post(
                    f"{BASE_URL}/login",
                    json=creds
                )
                if response.status_code == 200:
                    auth_data = response.json()
                    return auth_data.get("access_token")
            except Exception as e:
                print(f"  ⚠️  Login error with {creds['username']}: {e}")
                continue
        
        print("  ❌ Failed to authenticate")
        return None

async def check_worker_status(token):
    """Check worker status"""
    print("\n[1/4] Checking Worker Status...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{BASE_URL}/bitrix/sync/worker/status",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                data = response.json()
                status = data.get("data", {})
                print(f"  ✅ Worker Enabled: {status.get('worker_enabled')}")
                print(f"  ✅ Worker Running: {status.get('worker_running')}")
                print(f"  ✅ Worker Task Exists: {status.get('worker_task_exists')}")
                print(f"  ✅ Worker Task Status: {status.get('worker_task_status')}")
                print(f"  ✅ Pending Messages: {status.get('pending_messages_count')}")
                return status
            else:
                print(f"  ❌ Failed to get worker status: {response.status_code}")
                print(f"     Response: {response.text}")
                return None
        except Exception as e:
            print(f"  ❌ Error checking worker status: {e}")
            return None

async def check_queue_status(token):
    """Check queue status"""
    print("\n[2/4] Checking Queue Status...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{BASE_URL}/bitrix/sync/status",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                data = response.json()
                status = data.get("data", {})
                ops_stream = status.get("operations_stream", {})
                webhooks_stream = status.get("webhooks_stream", {})
                print(f"  ✅ Operations Stream Length: {ops_stream.get('length', 0)}")
                print(f"  ✅ Webhooks Stream Length: {webhooks_stream.get('length', 0)}")
                print(f"  ✅ Total Messages: {status.get('total_messages', 0)}")
                print(f"  ✅ Bitrix Configured: {status.get('bitrix_configured')}")
                return status
            else:
                print(f"  ❌ Failed to get queue status: {response.status_code}")
                print(f"     Response: {response.text}")
                return None
        except Exception as e:
            print(f"  ❌ Error checking queue status: {e}")
            return None

async def check_recent_logs():
    """Check recent logs for worker activity"""
    print("\n[3/4] Checking Recent Logs...")
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", "docker-compose.local.yml", "logs", "backend", "--tail", "100"],
            capture_output=True,
            text=True,
            timeout=10
        )
        logs = result.stdout
        
        # Check for key indicators
        worker_started = "Starting Bitrix worker" in logs or "Bitrix worker started" in logs
        queue_messages = logs.count("[QUEUE]")
        worker_messages = logs.count("[WORKER]")
        errors = logs.count("ERROR") + logs.count("error")
        
        print(f"  ✅ Worker Started: {worker_started}")
        print(f"  ✅ Queue Messages in Logs: {queue_messages}")
        print(f"  ✅ Worker Messages in Logs: {worker_messages}")
        print(f"  ⚠️  Errors in Logs: {errors}")
        
        # Show recent worker/queue messages
        lines = logs.split('\n')
        recent_worker = [line for line in lines if "[WORKER]" in line or "[QUEUE]" in line][-5:]
        if recent_worker:
            print(f"\n  Recent Worker/Queue Messages:")
            for line in recent_worker:
                print(f"    {line[:100]}...")
        
        return {
            "worker_started": worker_started,
            "queue_messages": queue_messages,
            "worker_messages": worker_messages,
            "errors": errors
        }
    except Exception as e:
        print(f"  ❌ Error checking logs: {e}")
        return None

async def test_order_update_trigger(token):
    """Test if order update triggers queue operation"""
    print("\n[4/4] Testing Order Update Trigger...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # First, get list of orders
            response = await client.get(
                f"{BASE_URL}/orders",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                orders = response.json()
                if orders:
                    order_id = orders[0].get("order_id")
                    print(f"  📝 Found order {order_id}, testing update...")
                    
                    # Update order
                    update_data = {
                        "special_instructions": f"Test update at {datetime.now().isoformat()}"
                    }
                    update_response = await client.put(
                        f"{BASE_URL}/orders/{order_id}",
                        headers={"Authorization": f"Bearer {token}"},
                        json=update_data
                    )
                    if update_response.status_code == 200:
                        print(f"  ✅ Order {order_id} updated successfully")
                        print(f"  ⏳ Waiting 3 seconds for queue operation...")
                        await asyncio.sleep(3)
                        
                        # Check logs for queue message
                        import subprocess
                        result = subprocess.run(
                            ["docker", "compose", "-f", "docker-compose.local.yml", "logs", "backend", "--tail", "20"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        logs = result.stdout
                        if "[QUEUE_DEAL_UPDATE]" in logs:
                            print(f"  ✅ Queue operation detected in logs!")
                            return True
                        else:
                            print(f"  ⚠️  No queue operation detected in recent logs")
                            return False
                    else:
                        print(f"  ❌ Failed to update order: {update_response.status_code}")
                        return False
                else:
                    print(f"  ⚠️  No orders found to test")
                    return False
            else:
                print(f"  ❌ Failed to get orders: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ❌ Error testing order update: {e}")
            return False

async def main():
    """Run all diagnostics"""
    print("=" * 60)
    print("Bitrix Redis Worker Diagnostics")
    print("=" * 60)
    
    # Get admin token
    print("\n[0/4] Authenticating...")
    token = await get_admin_token()
    if not token:
        print("  ❌ Cannot proceed without authentication")
        return
    
    print("  ✅ Authenticated successfully")
    
    # Run diagnostics
    worker_status = await check_worker_status(token)
    queue_status = await check_queue_status(token)
    log_info = await check_recent_logs()
    trigger_test = await test_order_update_trigger(token)
    
    # Summary
    print("\n" + "=" * 60)
    print("Diagnostic Summary")
    print("=" * 60)
    
    if worker_status:
        print(f"Worker Status: {'✅ Running' if worker_status.get('worker_running') else '❌ Not Running'}")
        print(f"Pending Messages: {worker_status.get('pending_messages_count', 0)}")
    
    if queue_status:
        print(f"Operations Queue: {queue_status.get('operations_stream', {}).get('length', 0)} messages")
        print(f"Bitrix Configured: {'✅ Yes' if queue_status.get('bitrix_configured') else '❌ No'}")
    
    if log_info:
        print(f"Worker Activity: {'✅ Active' if log_info.get('worker_messages', 0) > 0 else '⚠️  No activity'}")
    
    print(f"Order Update Trigger: {'✅ Working' if trigger_test else '❌ Not Working'}")

if __name__ == "__main__":
    asyncio.run(main())

