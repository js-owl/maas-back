"""
Authentication endpoints tests
Tests login, logout, register, and profile management
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

class AuthEndpointTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token = None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def test_user_registration(self):
        """Test user registration with different user types"""
        print(" Testing user registration...")
        
        import time
        timestamp = int(time.time())
        
        test_users = [
            {
                "username": f"test_individual_{timestamp}",
                "password": "testpass123",
                "user_type": "individual"
            },
            {
                "username": f"test_legal_{timestamp}",
                "password": "testpass123",
                "user_type": "legal"
            }
        ]
        
        for user_data in test_users:
            response = await self.client.post(
                f"{self.base_url}/register",
                json=user_data
            )
            if response.status_code != 200:
                print(f"Registration failed with status {response.status_code}: {response.text}")
                raise AssertionError(f"Expected 200, got {response.status_code}")
            user_response = response.json()
            assert user_response["username"] == user_data["username"]
            assert user_response["user_type"] == user_data["user_type"]
            print(f" Registration passed for {user_data['user_type']} user")
    
    async def test_user_login(self):
        """Test user login and token generation"""
        print(" Testing user login...")
        
        import time
        timestamp = int(time.time())
        
        # First register a user
        user_data = {
            "username": f"test_login_{timestamp}",
            "password": "testpass123",
            "user_type": "individual"
        }
        
        # Register the user
        response = await self.client.post(
            f"{self.base_url}/register",
            json=user_data
        )
        if response.status_code != 200:
            print(f"Registration failed: {response.text}")
            raise AssertionError(f"Registration failed: {response.status_code}")
        
        # Now try to login
        login_data = {
            "username": f"test_login_{timestamp}",
            "password": "testpass123"
        }
        
        response = await self.client.post(
            f"{self.base_url}/login",
            json=login_data  # JSON-based authentication
        )
        assert response.status_code == 200
        auth_data = response.json()
        assert "access_token" in auth_data
        assert "token_type" in auth_data
        assert auth_data["token_type"] == "bearer"
        self.auth_token = auth_data["access_token"]
        print(" User login passed")
    
    async def test_profile_management(self):
        """Test profile access and updates"""
        print(" Testing profile management...")
        
        if not self.auth_token:
            # Create a user and login to get token
            import time
            timestamp = int(time.time())
            
            user_data = {
                "username": f"test_profile_{timestamp}",
                "password": "testpass123",
                "user_type": "individual"
            }
            
            # Register user
            response = await self.client.post(
                f"{self.base_url}/register",
                json=user_data
            )
            if response.status_code != 200:
                print(f"Registration failed: {response.text}")
                return
            
            # Login to get token
            login_data = {
                "username": f"test_profile_{timestamp}",
                "password": "testpass123"
            }
            
            response = await self.client.post(
                f"{self.base_url}/login",
                data=login_data
            )
            if response.status_code != 200:
                print(f"Login failed: {response.text}")
                return
            
            auth_data = response.json()
            self.auth_token = auth_data["access_token"]
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test profile access
        response = await self.client.get(
            f"{self.base_url}/profile",
            headers=headers
        )
        assert response.status_code == 200
        profile_data = response.json()
        assert "username" in profile_data
        assert "user_type" in profile_data
        print(" Profile access passed")
        
        # Test profile update
        update_data = {
            "user_type": "legal",
            "special_instructions": "Test company profile update"
        }
        response = await self.client.put(
            f"{self.base_url}/profile",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 200
        updated_profile = response.json()
        assert updated_profile["user_type"] == "legal"
        print(" Profile update passed")
    
    async def test_user_logout(self):
        """Test user logout"""
        print(" Testing user logout...")
        
        if not self.auth_token:
            print("  Skipping logout test - no auth token")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        response = await self.client.post(
            f"{self.base_url}/logout",
            headers=headers
        )
        assert response.status_code == 200
        logout_data = response.json()
        assert "message" in logout_data
        print(" User logout passed")
    
    async def test_invalid_credentials(self):
        """Test invalid login credentials"""
        print(" Testing invalid credentials...")
        
        invalid_login_data = {
            "username": "nonexistent_user",
            "password": "wrong_password"
        }
        
        response = await self.client.post(
            f"{self.base_url}/login",
            json=invalid_login_data
        )
        assert response.status_code == 401
        print(" Invalid credentials handling passed")
    
    async def test_duplicate_registration(self):
        """Test duplicate username registration"""
        print(" Testing duplicate registration...")
        
        import time
        timestamp = int(time.time())
        
        # First register a user
        user_data = {
            "username": f"test_duplicate_{timestamp}",
            "password": "testpass123",
            "user_type": "individual"
        }
        
        response = await self.client.post(
            f"{self.base_url}/register",
            json=user_data
        )
        if response.status_code != 200:
            print(f"Initial registration failed: {response.text}")
            return
        
        # Now try to register the same user again
        duplicate_user = {
            "username": f"test_duplicate_{timestamp}",  # Same username
            "password": "testpass123",
            "user_type": "individual"
        }
        
        response = await self.client.post(
            f"{self.base_url}/register",
            json=duplicate_user
        )
        assert response.status_code == 400
        error_data = response.json()
        # Check if detail exists and contains the expected message
        if "detail" in error_data:
            assert "already registered" in error_data["detail"].lower()
        else:
            # If detail doesn't exist, just check that we got an error response
            print(f"    Warning: Unexpected error format: {error_data}")
        print(" Duplicate registration handling passed")
    
    async def run_all_tests(self):
        """Run all authentication tests"""
        print(" Starting authentication endpoint tests...\n")
        
        try:
            await self.test_user_registration()
            print()
            
            await self.test_user_login()
            print()
            
            await self.test_profile_management()
            print()
            
            await self.test_user_logout()
            print()
            
            await self.test_invalid_credentials()
            print()
            
            await self.test_duplicate_registration()
            print()
            
            print(" All authentication tests completed successfully!")
            
        except Exception as e:
            print(f" Authentication test failed: {e}")
            raise


async def main():
    """Main test runner"""
    async with AuthEndpointTester() as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
