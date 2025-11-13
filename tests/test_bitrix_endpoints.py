#!/usr/bin/env python3
"""
Test Bitrix endpoints
"""
import asyncio
import aiohttp
import json
from typing import Dict, Any

class TestBitrixEndpoints:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.auth_token = None
        self.admin_token = None

    async def run_all_tests(self):
        """Run all Bitrix endpoint tests"""
        print("🧪 Testing Bitrix Endpoints")
        print("=" * 50)
        
        # Test OPTIONS endpoints first
        await self.test_options_endpoints()
        
        # Test authentication
        await self.test_authentication()
        
        if not self.admin_token:
            print("❌ Cannot continue without admin authentication")
            return False
            
        # Test Bitrix sync endpoints
        await self.test_bitrix_sync_endpoints()
        
        # Test Bitrix webhook endpoint
        await self.test_bitrix_webhook_endpoint()
        
        print("✅ Bitrix endpoint tests completed")
        return True

    async def test_options_endpoints(self):
        """Test OPTIONS endpoints for CORS preflight"""
        print("\n🔍 Testing OPTIONS endpoints...")
        
        options_endpoints = [
            "/sync/process",
            "/sync/status",
            "/sync/queue",
            "/sync/all",
            "/sync/pending",
            "/bitrix/webhook"
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in options_endpoints:
                try:
                    async with session.options(f"{self.base_url}{endpoint}") as response:
                        if response.status == 200:
                            print(f"  ✅ OPTIONS {endpoint} - {response.status}")
                        else:
                            print(f"  ❌ OPTIONS {endpoint} - {response.status}")
                except Exception as e:
                    print(f"  ❌ OPTIONS {endpoint} - Error: {e}")

    async def test_authentication(self):
        """Test admin authentication"""
        print("\n🔐 Testing authentication...")
        
        # Test admin login
        await self.test_admin_login()

    async def test_admin_login(self):
        """Test admin login"""
        print("  Testing admin login...")
        
        admin_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/login",
                    json=admin_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.admin_token = data.get("access_token")
                        print(f"    ✅ Admin login successful")
                        return True
                    else:
                        print(f"    ❌ Admin login failed: {response.status}")
                        return False
            except Exception as e:
                print(f"    ❌ Admin login error: {e}")
                return False

    async def test_bitrix_sync_endpoints(self):
        """Test Bitrix sync endpoints"""
        print("\n🔄 Testing Bitrix sync endpoints...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        async with aiohttp.ClientSession() as session:
            # Test GET /sync/status
            try:
                async with session.get(
                    f"{self.base_url}/sync/status",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"    ✅ GET /sync/status - {response.status}")
                        print(f"      Status: {data}")
                    else:
                        print(f"    ❌ GET /sync/status - {response.status}")
            except Exception as e:
                print(f"    ❌ GET /sync/status error: {e}")
            
            # Test GET /sync/queue
            try:
                async with session.get(
                    f"{self.base_url}/sync/queue",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"    ✅ GET /sync/queue - {response.status}")
                        print(f"      Queue items: {len(data) if isinstance(data, list) else 'N/A'}")
                    else:
                        print(f"    ❌ GET /sync/queue - {response.status}")
            except Exception as e:
                print(f"    ❌ GET /sync/queue error: {e}")
            
            # Test POST /sync/process
            try:
                async with session.post(
                    f"{self.base_url}/sync/process",
                    json={"limit": 5},
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"    ✅ POST /sync/process - {response.status}")
                        print(f"      Processed: {data}")
                    else:
                        print(f"    ❌ POST /sync/process - {response.status}")
            except Exception as e:
                print(f"    ❌ POST /sync/process error: {e}")
            
            # Test POST /sync/all
            try:
                async with session.post(
                    f"{self.base_url}/sync/all",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"    ✅ POST /sync/all - {response.status}")
                        print(f"      Sync result: {data}")
                    else:
                        print(f"    ❌ POST /sync/all - {response.status}")
            except Exception as e:
                print(f"    ❌ POST /sync/all error: {e}")
            
            # Test POST /sync/pending
            try:
                async with session.post(
                    f"{self.base_url}/sync/pending",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"    ✅ POST /sync/pending - {response.status}")
                        print(f"      Pending sync result: {data}")
                    else:
                        print(f"    ❌ POST /sync/pending - {response.status}")
            except Exception as e:
                print(f"    ❌ POST /sync/pending error: {e}")

    async def test_bitrix_webhook_endpoint(self):
        """Test Bitrix webhook endpoint"""
        print("\n🔗 Testing Bitrix webhook endpoint...")
        
        # Test webhook with sample payload
        webhook_payload = {
            "event_type": "deal_updated",
            "entity_type": "deal",
            "entity_id": "12345",
            "data": {
                "id": "12345",
                "title": "Test Deal",
                "stage_id": "NEW",
                "opportunity": "1000.00"
            }
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/bitrix/webhook",
                    json=webhook_payload
                ) as response:
                    if response.status == 200:
                        data = await response.text()
                        print(f"    ✅ POST /bitrix/webhook - {response.status}")
                        print(f"      Response: {data}")
                    else:
                        print(f"    ❌ POST /bitrix/webhook - {response.status}")
            except Exception as e:
                print(f"    ❌ POST /bitrix/webhook error: {e}")
        
        # Test webhook with invalid JSON
        try:
            async with session.post(
                f"{self.base_url}/bitrix/webhook",
                data="invalid json"
            ) as response:
                if response.status == 400:
                    print(f"    ✅ POST /bitrix/webhook (invalid JSON) - {response.status}")
                else:
                    print(f"    ❌ POST /bitrix/webhook (invalid JSON) - {response.status}")
        except Exception as e:
            print(f"    ❌ POST /bitrix/webhook (invalid JSON) error: {e}")


async def main():
    """Main test function"""
    tester = TestBitrixEndpoints()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 All Bitrix endpoint tests passed!")
    else:
        print("\n❌ Some Bitrix endpoint tests failed!")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())
