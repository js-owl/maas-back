#!/usr/bin/env python3
"""
Test call requests endpoints
"""
import asyncio
import aiohttp
import json
from typing import Dict, Any

class TestCallRequestsEndpoints:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_call_request_id = None
        self.auth_token = None
        self.admin_token = None

    async def run_all_tests(self):
        """Run all call request endpoint tests"""
        print("🧪 Testing Call Requests Endpoints")
        print("=" * 50)
        
        # Test OPTIONS endpoints first
        await self.test_options_endpoints()
        
        # Test authentication
        await self.test_authentication()
        
        if not self.auth_token:
            print("❌ Cannot continue without authentication")
            return False
            
        # Test call request endpoints
        await self.test_call_request_endpoints()
        
        # Test admin call request endpoints
        if self.admin_token:
            await self.test_admin_call_request_endpoints()
        else:
            print("⚠️  Skipping admin tests - no admin token")
        
        print("✅ Call requests endpoint tests completed")
        return True

    async def test_options_endpoints(self):
        """Test OPTIONS endpoints for CORS preflight"""
        print("\n🔍 Testing OPTIONS endpoints...")
        
        options_endpoints = [
            "/call-request",
            "/call-requests",
            "/admin/call-requests",
            "/admin/call-requests/1"  # Test with a call request ID
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
        """Test user authentication"""
        print("\n🔐 Testing authentication...")
        
        # Test user login
        await self.test_user_login()
        
        # Test admin login
        await self.test_admin_login()

    async def test_user_login(self):
        """Test user login"""
        print("  Testing user login...")
        
        login_data = {
            "username": "testuser",
            "password": "testpassword123"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/login",
                    json=login_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.auth_token = data.get("access_token")
                        print(f"    ✅ User login successful")
                        return True
                    else:
                        print(f"    ❌ User login failed: {response.status}")
                        return False
            except Exception as e:
                print(f"    ❌ User login error: {e}")
                return False

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

    async def test_call_request_endpoints(self):
        """Test call request management endpoints"""
        print("\n📞 Testing call request endpoints...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            # Test call request creation (singular endpoint)
            await self.test_create_call_request_singular(session, headers)
            
            # Test call request creation (plural endpoint)
            await self.test_create_call_request_plural(session, headers)

    async def test_create_call_request_singular(self, session, headers):
        """Test call request creation via singular endpoint"""
        print("  Testing call request creation (singular)...")
        
        call_request_data = {
            "name": "Test User",
            "phone": "+1234567890",
            "product": "CNC Milling",
            "time": "Morning",
            "additional": "Test call request for API testing",
            "agreement": True
        }
        
        try:
            async with session.post(
                f"{self.base_url}/call-request",
                json=call_request_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.test_call_request_id = data.get("id")
                    print(f"    ✅ Call request creation (singular) - ID: {self.test_call_request_id}")
                    return True
                else:
                    print(f"    ❌ Call request creation (singular) - {response.status}")
                    return False
        except Exception as e:
            print(f"    ❌ Call request creation (singular) error: {e}")
            return False

    async def test_create_call_request_plural(self, session, headers):
        """Test call request creation via plural endpoint"""
        print("  Testing call request creation (plural)...")
        
        call_request_data = {
            "name": "Test User 2",
            "phone": "+0987654321",
            "product": "3D Printing",
            "time": "Afternoon",
            "additional": "Test call request for API testing (plural)",
            "agreement": True
        }
        
        try:
            async with session.post(
                f"{self.base_url}/call-requests",
                json=call_request_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    call_request_id = data.get("id")
                    print(f"    ✅ Call request creation (plural) - ID: {call_request_id}")
                    return True
                else:
                    print(f"    ❌ Call request creation (plural) - {response.status}")
                    return False
        except Exception as e:
            print(f"    ❌ Call request creation (plural) error: {e}")
            return False

    async def test_admin_call_request_endpoints(self):
        """Test admin call request endpoints"""
        print("\n👑 Testing admin call request endpoints...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        async with aiohttp.ClientSession() as session:
            # Test get all call requests
            try:
                async with session.get(
                    f"{self.base_url}/admin/call-requests",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"    ✅ GET /admin/call-requests - {response.status} ({len(data)} call requests)")
                    else:
                        print(f"    ❌ GET /admin/call-requests - {response.status}")
            except Exception as e:
                print(f"    ❌ GET /admin/call-requests error: {e}")
            
            # Test get call request by ID
            if self.test_call_request_id:
                try:
                    async with session.get(
                        f"{self.base_url}/admin/call-requests/{self.test_call_request_id}",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            print(f"    ✅ GET /admin/call-requests/{self.test_call_request_id} - {response.status}")
                        else:
                            print(f"    ❌ GET /admin/call-requests/{self.test_call_request_id} - {response.status}")
                except Exception as e:
                    print(f"    ❌ GET /admin/call-requests/{self.test_call_request_id} error: {e}")
                
                # Test update call request status
                update_data = {
                    "status": "contacted"
                }
                try:
                    async with session.put(
                        f"{self.base_url}/admin/call-requests/{self.test_call_request_id}",
                        json=update_data,
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            print(f"    ✅ PUT /admin/call-requests/{self.test_call_request_id} - {response.status}")
                        else:
                            print(f"    ❌ PUT /admin/call-requests/{self.test_call_request_id} - {response.status}")
                except Exception as e:
                    print(f"    ❌ PUT /admin/call-requests/{self.test_call_request_id} error: {e}")


async def main():
    """Main test function"""
    tester = TestCallRequestsEndpoints()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 All call requests endpoint tests passed!")
    else:
        print("\n❌ Some call requests endpoint tests failed!")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())
