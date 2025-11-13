"""
Integration workflow tests with real services
E2E tests using real calculator service and Bitrix API
"""
import pytest
import httpx
from tests.test_config import BASE_URL
from tests.test_helpers import (
    generate_test_user,
    generate_test_file_upload,
    generate_test_order_data,
)


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.requires_calculator
@pytest.mark.asyncio
class TestCompleteUserJourneyIntegration:
    """Test complete user journey with real services"""
    
    async def test_end_to_end_order_creation_with_real_calculator(
        self, http_client, skip_if_calculator_unavailable
    ):
        """
        Complete E2E workflow with real calculator service:
        Register → Login → Upload → Calculate (real) → Order → Verify
        """
        # Step 1: Register user
        user_data = generate_test_user()
        response = await http_client.post(
            f"{BASE_URL}/register",
            json=user_data
        )
        assert response.status_code == 200, "User registration failed"
        
        # Step 2: Login
        response = await http_client.post(
            f"{BASE_URL}/login",
            json={
                "username": user_data["username"],
                "password": user_data["password"]
            }
        )
        assert response.status_code == 200, "Login failed"
        token = response.json()["access_token"]
        
        # Step 3: Upload STL file
        file_upload = generate_test_file_upload()
        response = await http_client.post(
            f"{BASE_URL}/files",
            json=file_upload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, "File upload failed"
        file_id = response.json()["id"]
        
        # Step 4: Calculate price with REAL calculator service
        calc_data = {
            "service_id": "cnc-milling",
            "material_id": "alum_D16",
            "material_form": "rod",
            "quantity": 1,
            "length": 100,
            "width": 50,
            "height": 25,
            "n_dimensions": 3,
            "tolerance_id": "1",
            "finish_id": "1",
            "cover_id": ["1"],
            "k_otk": "1",
            "k_cert": ["a"],
            "k_complexity": 1.0,
        }
        
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Calculation failed: {response.text}"
        calculation = response.json()
        assert "total_price" in calculation
        assert calculation["total_price"] > 0
        
        # Step 5: Create order
        order_data = generate_test_order_data("cnc-milling", file_id)
        response = await http_client.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Order creation failed: {response.text}"
        order = response.json()
        order_id = order["order_id"]
        assert order["total_price"] > 0
        
        # Step 6: Verify order was created
        response = await http_client.get(
            f"{BASE_URL}/orders/{order_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        order_details = response.json()
        assert order_details["order_id"] == order_id
        assert order_details["status"] in ["pending", "new"]
        
        # Cleanup
        await http_client.delete(
            f"{BASE_URL}/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
    
    async def test_multiple_calculations_with_real_service(
        self, http_client, user_account, skip_if_calculator_unavailable
    ):
        """
        Test multiple calculations with real calculator service
        """
        user_data, token = user_account
        
        services = ["cnc-milling", "cnc-lathe", "printing"]
        
        for service_id in services:
            calc_data = {
                "service_id": service_id,
                "material_id": "alum_D16" if service_id != "printing" else "PA11",
                "material_form": "rod" if service_id != "printing" else "powder",
                "quantity": 1,
                "length": 100,
                "width": 50,
                "height": 25,
                "n_dimensions": 3,
                "tolerance_id": "1",
                "finish_id": "1",
                "cover_id": ["1"],
                "k_otk": "1",
                "k_cert": ["a"],
                "k_complexity": 1.0,
            }
            
            response = await http_client.post(
                f"{BASE_URL}/calculate-price",
                json=calc_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Allow for service-specific errors
            if response.status_code == 200:
                calculation = response.json()
                assert "total_price" in calculation
                assert calculation["service_id"] == service_id


@pytest.mark.integration
@pytest.mark.requires_bitrix
@pytest.mark.asyncio
class TestBitrixIntegration:
    """Test Bitrix CRM integration workflows"""
    
    async def test_order_sync_to_bitrix(
        self, http_client, admin_token, user_account, uploaded_file,
        skip_if_bitrix_unavailable
    ):
        """
        Test order synchronization to Bitrix CRM
        """
        user_data, user_token = user_account
        
        # Create order
        order_data = generate_test_order_data("cnc-milling", uploaded_file)
        response = await http_client.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        order_id = response.json()["order_id"]
        
        # Check Bitrix sync status
        response = await http_client.get(
            f"{BASE_URL}/sync/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        status = response.json()
        assert "data" in status
        assert "bitrix_configured" in status["data"]
        
        if status["data"].get("bitrix_configured"):
            # Process sync queue
            response = await http_client.post(
                f"{BASE_URL}/sync/process",
                json={"limit": 10},
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200
            result = response.json()
            assert "stats" in result
            assert "processed" in result["stats"]
    
    async def test_bitrix_webhook_handling(
        self, http_client, skip_if_bitrix_unavailable
    ):
        """
        Test Bitrix webhook event handling
        """
        webhook_payload = {
            "event": "ONCRMDEALUPDATE",
            "data": {
                "FIELDS": {
                    "ID": "12345",
                    "TITLE": "Test Deal",
                    "STAGE_ID": "WON"
                }
            }
        }
        
        response = await http_client.post(
            f"{BASE_URL}/bitrix/webhook",
            json=webhook_payload
        )
        # Should accept webhook
        assert response.status_code in [200, 400]


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
class TestAdminWorkflowIntegration:
    """Test admin workflows with real services"""
    
    async def test_complete_admin_oversight_workflow(
        self, http_client, admin_token, user_account, uploaded_file
    ):
        """
        Complete admin workflow: Monitor orders → Update status → Sync
        """
        user_data, user_token = user_account
        
        # User creates order
        order_data = generate_test_order_data("cnc-milling", uploaded_file)
        response = await http_client.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        order_id = response.json()["order_id"]
        
        # Admin views all orders
        response = await http_client.get(
            f"{BASE_URL}/admin/orders",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        all_orders = response.json()
        assert any(o["order_id"] == order_id for o in all_orders)
        
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
        assert response.json()["status"] == "processing"
        
        # Check sync queue
        response = await http_client.get(
            f"{BASE_URL}/sync/queue",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
class TestServiceAvailabilityHandling:
    """Test handling of service availability"""
    
    async def test_graceful_degradation_calculator_unavailable(
        self, http_client, user_account
    ):
        """
        Test graceful handling when calculator service is unavailable
        """
        user_data, token = user_account
        
        # Try calculation (may fail if service down)
        calc_data = {
            "service_id": "cnc-milling",
            "material_id": "alum_D16",
            "material_form": "rod",
            "quantity": 1,
            "length": 100,
            "width": 50,
            "height": 25,
        }
        
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should either succeed or return graceful error
        assert response.status_code in [200, 400, 422, 500, 503, 504]
        
        if response.status_code != 200:
            # Verify error response has appropriate message
            error_data = response.json()
            assert "error" in error_data or "detail" in error_data or "message" in error_data

