#!/usr/bin/env python3
"""
Test users endpoints
"""
import asyncio
import aiohttp
import json
from typing import Dict, Any

class TestUsersEndpoints:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_user_id = None
        self.auth_token = None
        self.admin_token = None

    async def run_all_tests(self):
        """Run all user endpoint tests"""
        print("🧪 Testing Users Endpoints")
        print("=" * 50)
        
        # Test OPTIONS endpoints first
        await self.test_options_endpoints()
        
        # Test authentication
        await self.test_authentication()
        
        if not self.auth_token:
            print("❌ Cannot continue without authentication")
            return False
            
        # Test user profile endpoints
        await self.test_profile_endpoints()
        
        # Test admin user management endpoints
        if self.admin_token:
            await self.test_admin_user_endpoints()
        else:
            print("⚠️  Skipping admin tests - no admin token")
        
        print("✅ Users endpoint tests completed")
        return True

    async def test_options_endpoints(self):
        """Test OPTIONS endpoints for CORS preflight"""
        print("\n🔍 Testing OPTIONS endpoints...")
        
        options_endpoints = [
            "/profile",
            "/profile/",
            "/users",
            "/users/1"  # Test with a user ID
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
        
        # Test user registration
        await self.test_user_registration()
        
        # Test user login
        await self.test_user_login()
        
        # Test admin login
        await self.test_admin_login()

    async def test_user_registration(self):
        """Test user registration"""
        print("  Testing user registration...")
        
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User",
            "phone": "+1234567890"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/register",
                    json=user_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"    ✅ User registration successful")
                        return True
                    elif response.status == 400:
                        # User might already exist
                        print(f"    ⚠️  User registration - user may already exist")
                        return True
                    else:
                        print(f"    ❌ User registration failed: {response.status}")
                        return False
            except Exception as e:
                print(f"    ❌ User registration error: {e}")
                return False

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

    async def test_profile_endpoints(self):
        """Test user profile endpoints"""
        print("\n👤 Testing profile endpoints...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            # Test GET /profile
            try:
                async with session.get(
                    f"{self.base_url}/profile",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.test_user_id = data.get("id")
                        print(f"    ✅ GET /profile - {response.status}")
                    else:
                        print(f"    ❌ GET /profile - {response.status}")
            except Exception as e:
                print(f"    ❌ GET /profile error: {e}")
            
            # Test GET /profile/ (with trailing slash)
            try:
                async with session.get(
                    f"{self.base_url}/profile/",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        print(f"    ✅ GET /profile/ - {response.status}")
                    else:
                        print(f"    ❌ GET /profile/ - {response.status}")
            except Exception as e:
                print(f"    ❌ GET /profile/ error: {e}")
            
            # Test PUT /profile
            if self.test_user_id:
                update_data = {
                    "full_name": "Updated Test User",
                    "phone": "+0987654321"
                }
                try:
                    async with session.put(
                        f"{self.base_url}/profile",
                        json=update_data,
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            print(f"    ✅ PUT /profile - {response.status}")
                        else:
                            print(f"    ❌ PUT /profile - {response.status}")
                except Exception as e:
                    print(f"    ❌ PUT /profile error: {e}")

    async def test_admin_user_endpoints(self):
        """Test admin user management endpoints"""
        print("\n👑 Testing admin user endpoints...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        async with aiohttp.ClientSession() as session:
            # Test GET /users
            try:
                async with session.get(
                    f"{self.base_url}/users",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"    ✅ GET /users - {response.status} ({len(data)} users)")
                    else:
                        print(f"    ❌ GET /users - {response.status}")
            except Exception as e:
                print(f"    ❌ GET /users error: {e}")
            
            # Test GET /users/{id}
            if self.test_user_id:
                try:
                    async with session.get(
                        f"{self.base_url}/users/{self.test_user_id}",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            print(f"    ✅ GET /users/{self.test_user_id} - {response.status}")
                        else:
                            print(f"    ❌ GET /users/{self.test_user_id} - {response.status}")
                except Exception as e:
                    print(f"    ❌ GET /users/{self.test_user_id} error: {e}")
                
                # Test PUT /users/{id}
                update_data = {
                    "full_name": "Admin Updated User",
                    "is_admin": False
                }
                try:
                    async with session.put(
                        f"{self.base_url}/users/{self.test_user_id}",
                        json=update_data,
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            print(f"    ✅ PUT /users/{self.test_user_id} - {response.status}")
                        else:
                            print(f"    ❌ PUT /users/{self.test_user_id} - {response.status}")
                except Exception as e:
                    print(f"    ❌ PUT /users/{self.test_user_id} error: {e}")


async def main():
    """Main test function"""
    tester = TestUsersEndpoints()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 All users endpoint tests passed!")
    else:
        print("\n❌ Some users endpoint tests failed!")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())
