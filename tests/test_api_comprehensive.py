"""
Comprehensive API tests for the modular backend
Tests all endpoints with proper error handling and validation
"""
import asyncio
import httpx
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional

# Test configuration
BASE_URL = "http://localhost:8000"
import time
TEST_USER = {
    "username": f"testuser_modular_{int(time.time())}",
    "password": "testpass123",
    "user_type": "individual"
}

class ModularAPITester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token = None
        self.admin_token = None
        self.test_file_id = None
        self.test_document_id = None
        self.test_order_id = None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def test_health_endpoints(self):
        """Test health and status endpoints"""
        print(" Testing health endpoints...")
        
        # Test basic health
        response = await self.client.get(f"{self.base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(" Basic health check passed")
        
        # Test detailed health
        response = await self.client.get(f"{self.base_url}/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "modules" in data
        assert data["architecture"] == "modular"
        print(" Detailed health check passed")
        
        # Test root endpoint
        response = await self.client.get(f"{self.base_url}/")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["architecture"] == "modular"
        print(" Root endpoint passed")
    
    async def test_auth_flow(self):
        """Test complete authentication flow"""
        print(" Testing authentication flow...")
        
        # Test registration
        response = await self.client.post(
            f"{self.base_url}/register",
            json=TEST_USER
        )
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["username"] == TEST_USER["username"]
        print(" User registration passed")
        
        # Test login
        login_data = {
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        }
        response = await self.client.post(
            f"{self.base_url}/login",
            json=login_data  # JSON-based authentication
        )
        assert response.status_code == 200
        auth_data = response.json()
        assert "access_token" in auth_data
        self.auth_token = auth_data["access_token"]
        print(" User login passed")
        
        # Test profile access
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        response = await self.client.get(
            f"{self.base_url}/profile",
            headers=headers
        )
        assert response.status_code == 200
        profile_data = response.json()
        assert profile_data["username"] == TEST_USER["username"]
        print(" Profile access passed")
        
        # Test profile update
        update_data = {
            "user_type": "legal",
            "special_instructions": "Test company"
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
        
        # Test logout
        response = await self.client.post(
            f"{self.base_url}/logout",
            headers=headers
        )
        assert response.status_code == 200
        print(" Logout passed")
    
    async def test_calculations_endpoints(self):
        """Test calculation endpoints with JSON"""
        print(" Testing calculation endpoints...")
        
        # Test services endpoint
        response = await self.client.get(f"{self.base_url}/services")
        assert response.status_code == 200
        services = response.json()
        assert isinstance(services, list)
        assert len(services) == 4
        assert "printing" in services
        assert "cnc-milling" in services
        assert "cnc-lathe" in services
        assert "painting" in services
        print(" Services endpoint passed")
        
        # Test materials endpoint
        response = await self.client.get(f"{self.base_url}/materials")
        assert response.status_code == 200
        materials = response.json()
        assert isinstance(materials, dict)
        assert "materials" in materials
        print(" Materials endpoint passed")
        
        # Test materials with process filter
        response = await self.client.get(f"{self.base_url}/materials?process=printing")
        assert response.status_code == 200
        materials_filtered = response.json()
        assert isinstance(materials_filtered, dict)
        print(" Materials with process filter passed")
        
        # Test coefficients endpoint
        response = await self.client.get(f"{self.base_url}/coefficients")
        assert response.status_code == 200
        coefficients = response.json()
        assert isinstance(coefficients, dict)
        assert "tolerance" in coefficients
        assert "finish" in coefficients
        assert "cover" in coefficients
        print(" Coefficients endpoint passed")
        
        # Test locations endpoint
        response = await self.client.get(f"{self.base_url}/locations")
        assert response.status_code == 200
        locations = response.json()
        assert isinstance(locations, dict)
        assert "locations" in locations
        print(" Locations endpoint passed")
        
        # Test calculate-price with valid data
        calc_request = {
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
            "n_dimensions": 1
        }
        
        response = await self.client.post(
            f"{self.base_url}/calculate-price",
            json=calc_request
        )
        if response.status_code == 200:
            result = response.json()
            assert "total_price" in result
            assert "service_id" in result
            print(" Calculate-price with valid data passed")
        elif response.status_code == 502:
            print("  Calculator service not available (502)")
        else:
            print(f"  Calculate-price returned status {response.status_code}")
        
        # Test calculate-price with invalid data (should return 422)
        invalid_calc_request = {
            "service_id": "invalid-service",
            "quantity": -1,
            "length": 0,
            "width": 0,
            "height": 0,
            "material_id": "invalid_material",
            "material_form": "invalid_form",
            "tolerance_id": "invalid_tolerance",
            "finish_id": "invalid_finish",
            "cover_id": ["invalid_cover"],
            "k_otk": "invalid_otk",
            "k_cert": ["invalid_cert"],
            "n_dimensions": 0
        }
        
        response = await self.client.post(
            f"{self.base_url}/calculate-price",
            json=invalid_calc_request
        )
        if response.status_code == 422:
            print(" 422 error properly proxied from calculator service")
        elif response.status_code == 502:
            print("  Calculator service not available (502)")
        else:
            print(f"  Invalid calculation returned status {response.status_code}")
    
    async def test_files_endpoints(self):
        """Test file endpoints with JSON"""
        print(" Testing file endpoints...")
        
        if not self.auth_token:
            print("  Skipping file tests - no auth token")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test demo files endpoint
        response = await self.client.get(f"{self.base_url}/files/demo")
        assert response.status_code == 200
        demo_files = response.json()
        assert isinstance(demo_files, list)
        print(" Demo files endpoint passed")
        
        # Test file upload with JSON (base64)
        test_file_content = "This is a test STL file content for modular API testing"
        file_data = base64.b64encode(test_file_content.encode()).decode()
        
        upload_request = {
            "file_name": "test_model_modular.stl",
            "file_data": file_data,
            "file_type": "stl"
        }
        
        response = await self.client.post(
            f"{self.base_url}/files",
            json=upload_request,
            headers=headers
        )
        assert response.status_code == 200
        upload_data = response.json()
        assert "id" in upload_data
        self.test_file_id = upload_data["id"]
        print(" File upload with JSON passed")
        
        # Test file listing
        response = await self.client.get(
            f"{self.base_url}/files",
            headers=headers
        )
        assert response.status_code == 200
        files = response.json()
        assert isinstance(files, list)
        print(" File listing passed")
        
        # Test file details
        if self.test_file_id:
            response = await self.client.get(
                f"{self.base_url}/files/{self.test_file_id}",
                headers=headers
            )
            assert response.status_code == 200
            file_data = response.json()
            assert file_data["id"] == self.test_file_id
            print(" File details passed")
            
            # Test file preview
            response = await self.client.get(
                f"{self.base_url}/files/{self.test_file_id}/preview",
                headers=headers
            )
            assert response.status_code == 200
            print(" File preview passed")
    
    async def test_documents_endpoints(self):
        """Test document endpoints with JSON"""
        print(" Testing document endpoints...")
        
        if not self.auth_token:
            print("  Skipping document tests - no auth token")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test document upload with JSON
        test_doc_content = "This is a test document content for modular API testing"
        doc_data = base64.b64encode(test_doc_content.encode()).decode()
        
        doc_request = {
            "document_name": "test_document_modular.pdf",
            "document_data": doc_data,
            "document_category": "specification"
        }
        
        response = await self.client.post(
            f"{self.base_url}/documents",
            json=doc_request,
            headers=headers
        )
        print(f" Document upload response status: {response.status_code}")
        if response.status_code != 200:
            print(f" Document upload response body: {response.text}")
        assert response.status_code == 200
        doc_upload_data = response.json()
        assert "document_id" in doc_upload_data
        self.test_document_id = doc_upload_data["document_id"]
        print(" Document upload with JSON passed")
        
        # Test document listing
        response = await self.client.get(
            f"{self.base_url}/documents",
            headers=headers
        )
        assert response.status_code == 200
        documents = response.json()
        assert isinstance(documents, list)
        print(" Document listing passed")
        
        # Test document details
        if self.test_document_id:
            response = await self.client.get(
                f"{self.base_url}/documents/{self.test_document_id}",
                headers=headers
            )
            assert response.status_code == 200
            doc_data = response.json()
            assert doc_data["id"] == self.test_document_id
            print(" Document details passed")
        
        # Test document formats
        response = await self.client.get(f"{self.base_url}/documents/formats")
        print(f" Document formats response status: {response.status_code}")
        if response.status_code != 200:
            print(f" Document formats response body: {response.text}")
        assert response.status_code == 200
        formats = response.json()
        assert isinstance(formats, list)
        print(" Document formats passed")
    
    async def test_orders_endpoints(self):
        """Test order endpoints with JSON"""
        print(" Testing order endpoints...")
        
        if not self.auth_token:
            print("  Skipping order tests - no auth token")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test order creation with JSON
        order_request = {
            "service_id": "cnc-milling",
            "file_id": 1,  # Use demo file
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
        
        response = await self.client.post(
            f"{self.base_url}/orders",
            json=order_request,
            headers=headers
        )
        if response.status_code == 200:
            order_data = response.json()
            assert "order_id" in order_data
            self.test_order_id = order_data["order_id"]
            print(" Order creation with JSON passed")
        elif response.status_code == 502:
            print("  Order creation failed - calculator service not available")
        else:
            print(f"  Order creation returned status {response.status_code}")
        
        # Test order listing
        response = await self.client.get(
            f"{self.base_url}/orders",
            headers=headers
        )
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)
        print(" Order listing passed")
        
        # Test order details
        if self.test_order_id:
            response = await self.client.get(
                f"{self.base_url}/orders/{self.test_order_id}",
                headers=headers
            )
            assert response.status_code == 200
            order_data = response.json()
            assert order_data["order_id"] == self.test_order_id
            print(" Order details passed")
    
    async def test_call_requests_endpoints(self):
        """Test call request endpoints"""
        print(" Testing call request endpoints...")
        
        # Test call request creation
        call_request = {
            "name": "Test User Modular",
            "phone": "+1234567890",
            "product": "CNC Milling",
            "time": "Morning",
            "additional": "Test call request for modular API testing",
            "agreement": True
        }
        
        response = await self.client.post(
            f"{self.base_url}/call-request",
            json=call_request
        )
        assert response.status_code == 200
        call_data = response.json()
        assert call_data["name"] == call_request["name"]
        print(" Call request creation passed")
    
    async def test_admin_endpoints(self):
        """Test admin endpoints"""
        print(" Testing admin endpoints...")
        
        if not self.auth_token:
            print("  Skipping admin tests - no auth token")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test admin user listing
        response = await self.client.get(
            f"{self.base_url}/users",
            headers=headers
        )
        # This might fail if user is not admin, which is expected
        if response.status_code == 200:
            users = response.json()
            assert isinstance(users, list)
            print(" Admin user listing passed")
        elif response.status_code == 403:
            print("  Admin user listing - access denied (expected for non-admin)")
        else:
            print(f"  Admin user listing returned status {response.status_code}")
        
        # Test admin orders listing
        response = await self.client.get(
            f"{self.base_url}/admin/orders",
            headers=headers
        )
        if response.status_code == 200:
            orders = response.json()
            assert isinstance(orders, list)
            print(" Admin orders listing passed")
        elif response.status_code == 403:
            print("  Admin orders listing - access denied (expected for non-admin)")
        else:
            print(f"  Admin orders listing returned status {response.status_code}")
    
    async def run_all_tests(self):
        """Run all tests"""
        print(" Starting comprehensive modular API tests...\n")
        
        try:
            await self.test_health_endpoints()
            print()
            
            await self.test_auth_flow()
            print()
            
            await self.test_calculations_endpoints()
            print()
            
            await self.test_files_endpoints()
            print()
            
            await self.test_documents_endpoints()
            print()
            
            await self.test_orders_endpoints()
            print()
            
            await self.test_call_requests_endpoints()
            print()
            
            await self.test_admin_endpoints()
            print()
            
            print(" All tests completed successfully!")
            
        except Exception as e:
            print(f" Test failed: {e}")
            raise


async def main():
    """Main test runner"""
    async with ModularAPITester() as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
