"""
Comprehensive integration tests for all endpoints
Tests the complete user journey and admin workflows
"""
import asyncio
import httpx
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

class ComprehensiveIntegrationTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token = None
        self.admin_token = None
        self.test_user_id = None
        self.test_file_id = None
        self.test_document_id = None
        self.test_order_id = None
        self.test_call_request_id = None

    async def cleanup(self):
        """Clean up test data"""
        if self.client:
            await self.client.aclose()

    async def test_server_health(self) -> bool:
        """Test server health endpoint"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                print("✅ Server health check passed")
                return True
            else:
                print(f"❌ Server health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Server health check error: {e}")
            return False

    async def test_admin_registration_and_login(self) -> bool:
        """Test admin registration and login"""
        try:
            # Try to login as admin
            login_data = {
                "username": "admin",
                "password": "admin123"
            }
            
            response = await self.client.post(
                f"{self.base_url}/login",
                json=login_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data["access_token"]
                print("✅ Admin login successful")
                return True
            else:
                print(f"❌ Admin login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Admin login error: {e}")
            return False

    async def test_user_registration_and_login(self) -> bool:
        """Test user registration and login"""
        try:
            # Register new user
            timestamp = int(time.time())
            user_data = {
                "username": f"testuser_integration_{timestamp}",
                "password": "testpass123",
                "user_type": "individual"
            }
            
            response = await self.client.post(
                f"{self.base_url}/register",
                json=user_data
            )
            
            if response.status_code == 200:
                print("✅ User registration successful")
                
                # Login as user
                login_data = {
                    "username": user_data["username"],
                    "password": user_data["password"]
                }
                
                response = await self.client.post(
                    f"{self.base_url}/login",
                    json=login_data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.auth_token = data["access_token"]
                    print("✅ User login successful")
                    return True
                else:
                    print(f"❌ User login failed: {response.status_code} - {response.text}")
                    return False
            else:
                print(f"❌ User registration failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ User registration/login error: {e}")
            return False

    async def test_file_upload(self) -> bool:
        """Test file upload"""
        try:
            if not self.auth_token:
                print("❌ No auth token for file upload")
                return False
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Create test STL file content
            stl_content = """solid test
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0 1 0
    endloop
  endfacet
endsolid test"""
            
            file_data = {
                "file_name": "test_integration.stl",
                "file_data": stl_content.encode('utf-8').hex(),
                "file_type": "stl"
            }
            
            response = await self.client.post(
                f"{self.base_url}/files",
                json=file_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test_file_id = data["file_id"]
                print(f"✅ File upload successful: ID {self.test_file_id}")
                return True
            else:
                print(f"❌ File upload failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ File upload error: {e}")
            return False

    async def test_document_upload(self) -> bool:
        """Test document upload"""
        try:
            if not self.auth_token:
                print("❌ No auth token for document upload")
                return False
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Create test PDF content
            pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF"
            
            doc_data = {
                "document_name": "test_integration.pdf",
                "document_data": pdf_content.hex(),
                "document_category": "technical_drawing"
            }
            
            response = await self.client.post(
                f"{self.base_url}/documents",
                json=doc_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test_document_id = data["document_id"]
                print(f"✅ Document upload successful: ID {self.test_document_id}")
                return True
            else:
                print(f"❌ Document upload failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Document upload error: {e}")
            return False

    async def test_order_creation(self) -> bool:
        """Test order creation"""
        try:
            if not self.auth_token or not self.test_file_id:
                print("❌ Missing auth token or file ID for order creation")
                return False
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            order_data = {
                "service_id": "printing",
                "file_id": self.test_file_id,
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
                "document_ids": [self.test_document_id] if self.test_document_id else []
            }
            
            response = await self.client.post(
                f"{self.base_url}/orders",
                json=order_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test_order_id = data["order_id"]
                print(f"✅ Order creation successful: ID {self.test_order_id}")
                return True
            else:
                print(f"❌ Order creation failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Order creation error: {e}")
            return False

    async def test_call_request_creation(self) -> bool:
        """Test call request creation"""
        try:
            call_request_data = {
                "name": "Test User",
                "phone": "+1234567890",
                "email": "test@example.com",
                "product": "CNC Milling",
                "date": "2024-01-15",
                "time": "10:00",
                "additional": "Test call request for integration testing"
            }
            
            response = await self.client.post(
                f"{self.base_url}/call-requests",
                json=call_request_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test_call_request_id = data["id"]
                print(f"✅ Call request creation successful: ID {self.test_call_request_id}")
                return True
            else:
                print(f"❌ Call request creation failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Call request creation error: {e}")
            return False

    async def test_admin_endpoints(self) -> bool:
        """Test admin-only endpoints"""
        try:
            if not self.admin_token:
                print("❌ No admin token for admin endpoint tests")
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Test get all users
            response = await self.client.get(
                f"{self.base_url}/users",
                headers=headers
            )
            if response.status_code != 200:
                print(f"❌ Get all users failed: {response.status_code}")
                return False
            
            # Test get all orders
            response = await self.client.get(
                f"{self.base_url}/orders",
                headers=headers
            )
            if response.status_code != 200:
                print(f"❌ Get all orders failed: {response.status_code}")
                return False
            
            # Test get all call requests
            response = await self.client.get(
                f"{self.base_url}/admin/call-requests",
                headers=headers
            )
            if response.status_code != 200:
                print(f"❌ Get all call requests failed: {response.status_code}")
                return False
            
            # Test Bitrix sync status
            response = await self.client.get(
                f"{self.base_url}/sync/status",
                headers=headers
            )
            if response.status_code != 200:
                print(f"❌ Get Bitrix sync status failed: {response.status_code}")
                return False
            
            print("✅ All admin endpoints working")
            return True
            
        except Exception as e:
            print(f"❌ Admin endpoint test error: {e}")
            return False

    async def test_calculator_endpoints(self) -> bool:
        """Test calculator service endpoints"""
        try:
            # Test proxy endpoints
            response = await self.client.get(f"{self.base_url}/services")
            if response.status_code != 200:
                print(f"❌ Get services failed: {response.status_code}")
                return False
            
            response = await self.client.get(f"{self.base_url}/materials")
            if response.status_code != 200:
                print(f"❌ Get materials failed: {response.status_code}")
                return False
            
            response = await self.client.get(f"{self.base_url}/coefficients")
            if response.status_code != 200:
                print(f"❌ Get coefficients failed: {response.status_code}")
                return False
            
            response = await self.client.get(f"{self.base_url}/locations")
            if response.status_code != 200:
                print(f"❌ Get locations failed: {response.status_code}")
                return False
            
            print("✅ All calculator proxy endpoints working")
            return True
            
        except Exception as e:
            print(f"❌ Calculator endpoint test error: {e}")
            return False

    async def run_all_tests(self) -> bool:
        """Run all integration tests"""
        print("🚀 Starting comprehensive integration tests...\n")
        
        tests = [
            ("Server Health", self.test_server_health),
            ("Admin Login", self.test_admin_registration_and_login),
            ("User Registration/Login", self.test_user_registration_and_login),
            ("File Upload", self.test_file_upload),
            ("Document Upload", self.test_document_upload),
            ("Order Creation", self.test_order_creation),
            ("Call Request Creation", self.test_call_request_creation),
            ("Admin Endpoints", self.test_admin_endpoints),
            ("Calculator Endpoints", self.test_calculator_endpoints),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"Testing {test_name}...")
            try:
                if await test_func():
                    passed += 1
                    print(f"✅ {test_name} passed\n")
                else:
                    print(f"❌ {test_name} failed\n")
            except Exception as e:
                print(f"❌ {test_name} error: {e}\n")
        
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All integration tests passed!")
            return True
        else:
            print(f"⚠️  {total - passed} tests failed")
            return False

async def main():
    """Main test runner"""
    tester = ComprehensiveIntegrationTester()
    try:
        success = await tester.run_all_tests()
        return success
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
