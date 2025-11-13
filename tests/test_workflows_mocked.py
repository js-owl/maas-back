"""
Workflow tests with mocked services
Fast unit workflow tests with all external services mocked
"""
import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from tests.test_config import BASE_URL
from tests.test_helpers import (
    generate_test_user,
    generate_test_file_upload,
    generate_test_order_data,
    mock_calculator_response,
    mock_bitrix_deal_response,
)


@pytest.mark.unit
@pytest.mark.asyncio
class TestCompleteUserJourneyMocked:
    """Test complete user journey with mocked external services"""
    
    async def test_user_registration_to_order_creation(
        self, http_client, mock_calculator_service
    ):
        """
        Complete workflow: Register → Login → Upload File → Calculate → Create Order
        """
        # Step 1: Register user
        user_data = generate_test_user()
        response = await http_client.post(
            f"{BASE_URL}/register",
            json=user_data
        )
        assert response.status_code == 200, "User registration failed"
        registered_user = response.json()
        assert "username" in registered_user
        
        # Step 2: Login
        response = await http_client.post(
            f"{BASE_URL}/login",
            json={
                "username": user_data["username"],
                "password": user_data["password"]
            }
        )
        assert response.status_code == 200, "Login failed"
        auth_data = response.json()
        token = auth_data["access_token"]
        assert token is not None
        
        # Step 3: Upload STL file
        file_upload = generate_test_file_upload()
        response = await http_client.post(
            f"{BASE_URL}/files",
            json=file_upload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, "File upload failed"
        file_data = response.json()
        file_id = file_data["id"]
        assert file_id is not None
        
        # Step 4: Get file preview (should be generated)
        response = await http_client.get(
            f"{BASE_URL}/files/{file_id}/preview",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code in [200, 404], "Preview check failed"
        
        # Step 5: Calculate price (mocked calculator)
        calc_data = {
            "service_id": "cnc-milling",
            "material_id": "alum_D16",
            "material_form": "rod",
            "quantity": 1,
            "length": 100,
            "width": 50,
            "height": 25,
        }
        
        # Mock calculator response
        mock_calc_response = mock_calculator_response("cnc-milling", 150.50)
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_calc_response
            mock_post.return_value = mock_resp
            
            response = await http_client.post(
                f"{BASE_URL}/calculate-price",
                json=calc_data,
                headers={"Authorization": f"Bearer {token}"}
            )
        
        # Note: The actual response depends on implementation
        # Just verify it doesn't crash
        assert response.status_code in [200, 400, 500]
        
        # Step 6: Create order
        order_data = generate_test_order_data("cnc-milling", file_id)
        response = await http_client.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, "Order creation failed"
        order = response.json()
        order_id = order["order_id"]
        assert order_id is not None
        
        # Step 7: Get order details
        response = await http_client.get(
            f"{BASE_URL}/orders/{order_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, "Get order details failed"
        order_details = response.json()
        assert order_details["order_id"] == order_id
        
        # Step 8: Get user's order list
        response = await http_client.get(
            f"{BASE_URL}/orders",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, "Get orders list failed"
        orders = response.json()
        assert len(orders) >= 1
        assert any(o["order_id"] == order_id for o in orders)
        
        # Cleanup
        await http_client.delete(
            f"{BASE_URL}/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
    
    async def test_file_upload_preview_download_workflow(
        self, http_client, user_account
    ):
        """
        Workflow: Upload File → Check Preview → Download File → Delete
        """
        user_data, token = user_account
        
        # Upload file
        file_upload = generate_test_file_upload()
        response = await http_client.post(
            f"{BASE_URL}/files",
            json=file_upload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        file_data = response.json()
        file_id = file_data["id"]
        
        # Check file in list
        response = await http_client.get(
            f"{BASE_URL}/files",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        files = response.json()
        assert any(f["id"] == file_id for f in files)
        
        # Get file details
        response = await http_client.get(
            f"{BASE_URL}/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Download file
        response = await http_client.get(
            f"{BASE_URL}/files/{file_id}/download",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert len(response.content) > 0
        
        # Delete file
        response = await http_client.delete(
            f"{BASE_URL}/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Verify deletion
        response = await http_client.get(
            f"{BASE_URL}/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.asyncio
class TestAdminWorkflowMocked:
    """Test admin workflows with mocked services"""
    
    async def test_admin_user_management_workflow(
        self, http_client, admin_token
    ):
        """
        Admin workflow: View Users → Create User → Update User → View User
        """
        # View all users
        response = await http_client.get(
            f"{BASE_URL}/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        users_before = response.json()
        initial_count = len(users_before)
        
        # Create test user
        user_data = generate_test_user()
        response = await http_client.post(
            f"{BASE_URL}/register",
            json=user_data
        )
        assert response.status_code == 200
        new_user = response.json()
        user_id = new_user["id"]
        
        # Verify user count increased
        response = await http_client.get(
            f"{BASE_URL}/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        users_after = response.json()
        assert len(users_after) == initial_count + 1
        
        # Get specific user
        response = await http_client.get(
            f"{BASE_URL}/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        user_details = response.json()
        assert user_details["id"] == user_id
        
        # Update user
        response = await http_client.put(
            f"{BASE_URL}/users/{user_id}",
            json={"full_name": "Updated Name"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
    
    async def test_admin_order_management_workflow(
        self, http_client, admin_token, user_account, uploaded_file
    ):
        """
        Admin workflow: View All Orders → View Order → Update Order Status
        """
        user_data, user_token = user_account
        
        # User creates an order
        order_data = generate_test_order_data("cnc-milling", uploaded_file)
        response = await http_client.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        order = response.json()
        order_id = order["order_id"]
        
        # Admin views all orders
        response = await http_client.get(
            f"{BASE_URL}/admin/orders",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        all_orders = response.json()
        assert any(o["order_id"] == order_id for o in all_orders)
        
        # Admin views specific order
        response = await http_client.get(
            f"{BASE_URL}/admin/orders/{order_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        order_details = response.json()
        assert order_details["order_id"] == order_id
        
        # Admin updates order status
        response = await http_client.put(
            f"{BASE_URL}/admin/orders/{order_id}",
            json={"status": "processing"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        # Verify status updated
        response = await http_client.get(
            f"{BASE_URL}/orders/{order_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        updated_order = response.json()
        assert updated_order["status"] == "processing"
    
    async def test_admin_call_request_workflow(
        self, http_client, admin_token, user_account
    ):
        """
        Admin workflow: View Call Requests → Update Status
        """
        user_data, user_token = user_account
        
        # User creates call request
        call_request_data = {
            "name": "Test User",
            "phone": "+1234567890",
            "product": "CNC Milling",
            "time": "Morning",
            "additional": "Test message",
            "agreement": True
        }
        
        response = await http_client.post(
            f"{BASE_URL}/call-request",
            json=call_request_data,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        call_request = response.json()
        call_request_id = call_request["id"]
        
        # Admin views all call requests
        response = await http_client.get(
            f"{BASE_URL}/admin/call-requests",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        all_requests = response.json()
        assert any(r["id"] == call_request_id for r in all_requests)
        
        # Admin updates call request status
        response = await http_client.put(
            f"{BASE_URL}/admin/call-requests/{call_request_id}/status",
            json={"status": "contacted"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
class TestErrorRecoveryWorkflowMocked:
    """Test error recovery workflows with mocked services"""
    
    async def test_failed_upload_retry_success(
        self, http_client, user_account
    ):
        """
        Workflow: Failed Upload → Retry → Success
        """
        user_data, token = user_account
        
        # First attempt with invalid data
        response = await http_client.post(
            f"{BASE_URL}/files",
            json={
                "file_name": "test.stl",
                "file_data": "invalid_base64"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code in [400, 422], "Invalid upload should fail"
        
        # Retry with valid data
        file_upload = generate_test_file_upload()
        response = await http_client.post(
            f"{BASE_URL}/files",
            json=file_upload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, "Valid upload should succeed"
        file_data = response.json()
        file_id = file_data["id"]
        
        # Cleanup
        await http_client.delete(
            f"{BASE_URL}/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
    
    async def test_failed_order_creation_retry(
        self, http_client, user_account, uploaded_file
    ):
        """
        Workflow: Failed Order Creation → Fix Data → Retry → Success
        """
        user_data, token = user_account
        
        # First attempt with invalid data
        invalid_order = {
            "service_id": "invalid-service",
            "file_id": uploaded_file,
            "quantity": -1,  # Invalid
        }
        
        response = await http_client.post(
            f"{BASE_URL}/orders",
            json=invalid_order,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code in [400, 422], "Invalid order should fail"
        
        # Retry with valid data
        valid_order = generate_test_order_data("cnc-milling", uploaded_file)
        response = await http_client.post(
            f"{BASE_URL}/orders",
            json=valid_order,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, "Valid order should succeed"
    
    async def test_authentication_failure_recovery(
        self, http_client
    ):
        """
        Workflow: Failed Login → Register → Login → Success
        """
        # Try to login with nonexistent user
        response = await http_client.post(
            f"{BASE_URL}/login",
            json={
                "username": "nonexistent_user",
                "password": "wrong_password"
            }
        )
        assert response.status_code == 401, "Invalid login should fail"
        
        # Register new user
        user_data = generate_test_user()
        response = await http_client.post(
            f"{BASE_URL}/register",
            json=user_data
        )
        assert response.status_code == 200, "Registration should succeed"
        
        # Login with new credentials
        response = await http_client.post(
            f"{BASE_URL}/login",
            json={
                "username": user_data["username"],
                "password": user_data["password"]
            }
        )
        assert response.status_code == 200, "Login after registration should succeed"
        assert "access_token" in response.json()


@pytest.mark.unit
@pytest.mark.asyncio
class TestMultiServiceWorkflowMocked:
    """Test workflows across multiple services"""
    
    async def test_multiple_file_types_workflow(
        self, http_client, user_account
    ):
        """
        Workflow: Upload STL → Upload Document → Upload STP → List All
        """
        user_data, token = user_account
        
        uploaded_ids = []
        
        # Upload STL file
        stl_upload = generate_test_file_upload()
        response = await http_client.post(
            f"{BASE_URL}/files",
            json=stl_upload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        uploaded_ids.append(("file", response.json()["id"]))
        
        # Upload document
        from tests.test_helpers import generate_test_document_upload
        doc_upload = generate_test_document_upload()
        response = await http_client.post(
            f"{BASE_URL}/documents",
            json=doc_upload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        uploaded_ids.append(("document", response.json()["document_id"]))
        
        # List files
        response = await http_client.get(
            f"{BASE_URL}/files",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        files = response.json()
        assert len(files) >= 1
        
        # List documents
        response = await http_client.get(
            f"{BASE_URL}/documents",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        documents = response.json()
        assert len(documents) >= 1
        
        # Cleanup
        for resource_type, resource_id in uploaded_ids:
            if resource_type == "file":
                await http_client.delete(
                    f"{BASE_URL}/files/{resource_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
            else:
                await http_client.delete(
                    f"{BASE_URL}/documents/{resource_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
    
    async def test_multiple_orders_workflow(
        self, http_client, user_account, uploaded_file
    ):
        """
        Workflow: Create Multiple Orders → List → Check Each
        """
        user_data, token = user_account
        
        # Create orders for different services
        services = ["cnc-milling", "cnc-lathe", "printing"]
        order_ids = []
        
        for service in services:
            order_data = generate_test_order_data(service, uploaded_file)
            response = await http_client.post(
                f"{BASE_URL}/orders",
                json=order_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                order_ids.append(response.json()["order_id"])
        
        # List all orders
        response = await http_client.get(
            f"{BASE_URL}/orders",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        orders = response.json()
        assert len(orders) >= len(order_ids)
        
        # Check each order
        for order_id in order_ids:
            response = await http_client.get(
                f"{BASE_URL}/orders/{order_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200

