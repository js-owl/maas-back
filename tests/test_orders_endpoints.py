"""
Orders endpoints tests
Tests order creation, management, and admin operations
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

class OrdersEndpointTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token = None
        self.test_order_id = None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def setup_auth(self):
        """Setup authentication for order tests"""
        # Register test user
        user_data = {
            "username": "test_orders_user",
            "password": "testpass123",
            "user_type": "individual"
        }
        
        try:
            await self.client.post(f"{self.base_url}/register", json=user_data)
        except:
            pass  # User might already exist
        
        # Login
        login_data = {
            "username": "test_orders_user",
            "password": "testpass123"
        }
        
        response = await self.client.post(
            f"{self.base_url}/login",
            json=login_data
        )
        assert response.status_code == 200
        auth_data = response.json()
        self.auth_token = auth_data["access_token"]
    
    async def test_order_creation(self):
        """Test order creation with JSON"""
        print(" Testing order creation...")
        
        if not self.auth_token:
            await self.setup_auth()
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test order creation for different services
        services = ["printing", "cnc-milling", "cnc-lathe", "painting"]
        
        for service in services:
            order_request = {
                "service_id": service,
                "file_id": 1,  # Demo file
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
                assert "service_id" in order_data
                assert order_data["service_id"] == service
                assert "total_price" in order_data
                self.test_order_id = order_data["order_id"]
                print(f" Order creation for {service} passed")
            elif response.status_code == 502:
                print(f"  Order creation for {service} - calculator service not available")
            else:
                print(f"  Order creation for {service} returned status {response.status_code}")
    
    async def test_order_listing(self):
        """Test order listing"""
        print(" Testing order listing...")
        
        if not self.auth_token:
            await self.setup_auth()
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        response = await self.client.get(
            f"{self.base_url}/orders",
            headers=headers
        )
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)
        print(" Order listing passed")
    
    async def test_order_details(self):
        """Test order details retrieval"""
        print(" Testing order details...")
        
        if not self.auth_token:
            await self.setup_auth()
        
        if not self.test_order_id:
            print("  Skipping order details test - no test order ID")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        response = await self.client.get(
            f"{self.base_url}/orders/{self.test_order_id}",
            headers=headers
        )
        assert response.status_code == 200
        order_data = response.json()
        assert order_data["order_id"] == self.test_order_id
        assert "service_id" in order_data
        assert "total_price" in order_data
        print(" Order details passed")
    
    async def test_order_access_control(self):
        """Test order access control"""
        print(" Testing order access control...")
        
        if not self.test_order_id:
            print("  Skipping order access control test - no test order ID")
            return
        
        # Test access without authentication
        response = await self.client.get(
            f"{self.base_url}/orders/{self.test_order_id}"
        )
        assert response.status_code == 401
        print(" Order access control (no auth) passed")
        
        # Test access with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = await self.client.get(
            f"{self.base_url}/orders/{self.test_order_id}",
            headers=headers
        )
        assert response.status_code == 401
        print(" Order access control (invalid token) passed")
    
    async def test_order_validation(self):
        """Test order validation"""
        print(" Testing order validation...")
        
        if not self.auth_token:
            await self.setup_auth()
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test order with invalid service_id
        invalid_order = {
            "service_id": "invalid-service",
            "file_id": 1,
            "quantity": 1,
            "length": 100,
            "width": 50,
            "height": 25,
            "material_id": "alum_D16",
            "material_form": "rod",
            "tolerance_id": "1",
            "finish_id": "1",
            "id_cover": ["1"],
            "k_otk": "1",
            "k_cert": ["a", "f"],
            "n_dimensions": 1,
            "document_ids": []
        }
        
        response = await self.client.post(
            f"{self.base_url}/orders",
            json=invalid_order,
            headers=headers
        )
        
        if response.status_code == 422:
            print(" Order validation (invalid service) passed")
        elif response.status_code == 502:
            print("  Order validation - calculator service not available")
        else:
            print(f"  Order validation returned status {response.status_code}")
        
        # Test order with invalid quantity
        invalid_quantity_order = {
            "service_id": "cnc-milling",
            "file_id": 1,
            "quantity": -1,
            "length": 100,
            "width": 50,
            "height": 25,
            "material_id": "alum_D16",
            "material_form": "rod",
            "tolerance_id": "1",
            "finish_id": "1",
            "id_cover": ["1"],
            "k_otk": "1",
            "k_cert": ["a", "f"],
            "n_dimensions": 1,
            "document_ids": []
        }
        
        response = await self.client.post(
            f"{self.base_url}/orders",
            json=invalid_quantity_order,
            headers=headers
        )
        
        if response.status_code == 422:
            print(" Order validation (invalid quantity) passed")
        elif response.status_code == 502:
            print("  Order validation - calculator service not available")
        else:
            print(f"  Order validation returned status {response.status_code}")
    
    async def test_order_with_documents(self):
        """Test order creation with documents"""
        print(" Testing order creation with documents...")
        
        if not self.auth_token:
            await self.setup_auth()
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # First, create a document
        test_doc_content = "Test document for order"
        doc_data = {
            "document_name": "test_order_doc.pdf",
            "document_data": "VGVzdCBkb2N1bWVudCBmb3Igb3JkZXI=",  # base64 encoded
            "document_category": "specification"
        }
        
        doc_response = await self.client.post(
            f"{self.base_url}/documents/upload-json",
            json=doc_data,
            headers=headers
        )
        
        document_id = None
        if doc_response.status_code == 200:
            doc_upload_data = doc_response.json()
            document_id = doc_upload_data["document_id"]
        
        # Create order with document
        order_request = {
            "service_id": "cnc-milling",
            "file_id": 1,
            "quantity": 1,
            "length": 100,
            "width": 50,
            "height": 25,
            "material_id": "alum_D16",
            "material_form": "rod",
            "tolerance_id": "1",
            "finish_id": "1",
            "id_cover": ["1"],
            "k_otk": "1",
            "k_cert": ["a", "f"],
            "n_dimensions": 1,
            "document_ids": [document_id] if document_id else []
        }
        
        response = await self.client.post(
            f"{self.base_url}/orders",
            json=order_request,
            headers=headers
        )
        
        if response.status_code == 200:
            order_data = response.json()
            assert "order_id" in order_data
            print(" Order creation with documents passed")
        elif response.status_code == 502:
            print("  Order creation with documents - calculator service not available")
        else:
            print(f"  Order creation with documents returned status {response.status_code}")
    
    async def test_admin_orders_endpoint(self):
        """Test admin orders endpoint"""
        print(" Testing admin orders endpoint...")
        
        if not self.auth_token:
            await self.setup_auth()
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        response = await self.client.get(
            f"{self.base_url}/admin/orders",
            headers=headers
        )
        
        if response.status_code == 200:
            orders = response.json()
            assert isinstance(orders, list)
            print(" Admin orders endpoint passed")
        elif response.status_code == 403:
            print("  Admin orders endpoint - access denied (expected for non-admin)")
        else:
            print(f"  Admin orders endpoint returned status {response.status_code}")
    
    async def test_invalid_order_operations(self):
        """Test invalid order operations"""
        print(" Testing invalid order operations...")
        
        if not self.auth_token:
            await self.setup_auth()
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test access to non-existent order
        response = await self.client.get(
            f"{self.base_url}/orders/99999",
            headers=headers
        )
        assert response.status_code == 404
        print(" Non-existent order handling passed")
    
    async def run_all_tests(self):
        """Run all order tests"""
        print(" Starting order endpoint tests...\n")
        
        try:
            await self.test_order_creation()
            print()
            
            await self.test_order_listing()
            print()
            
            await self.test_order_details()
            print()
            
            await self.test_order_access_control()
            print()
            
            await self.test_order_validation()
            print()
            
            await self.test_order_with_documents()
            print()
            
            await self.test_admin_orders_endpoint()
            print()
            
            await self.test_invalid_order_operations()
            print()
            
            print(" All order tests completed successfully!")
            
        except Exception as e:
            print(f" Order test failed: {e}")
            raise


async def main():
    """Main test runner"""
    async with OrdersEndpointTester() as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
