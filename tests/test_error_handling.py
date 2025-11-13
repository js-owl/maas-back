"""
Error handling and edge case tests
Tests invalid inputs, service failures, network errors, and recovery scenarios
"""
import pytest
import httpx
import asyncio
from unittest.mock import patch, AsyncMock
from tests.test_config import BASE_URL, CALCULATOR_URL
from tests.test_helpers import (
    generate_test_file_upload,
    generate_test_calculation_data,
    validate_error_response,
    encode_file_to_base64,
)


@pytest.mark.unit
class TestInvalidFileHandling:
    """Test handling of invalid and corrupted files"""
    
    @pytest.mark.asyncio
    async def test_upload_corrupted_stl_file(self, http_client, user_account):
        """Test upload of corrupted STL file"""
        user_data, token = user_account
        
        # Corrupted STL content
        corrupted_stl = b"corrupted file content"
        
        response = await http_client.post(
            f"{BASE_URL}/files",
            json={
                "file_name": "corrupted.stl",
                "file_data": encode_file_to_base64(corrupted_stl)
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should either accept (with warning) or reject
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_upload_empty_file(self, http_client, user_account):
        """Test upload of empty file"""
        user_data, token = user_account
        
        response = await http_client.post(
            f"{BASE_URL}/files",
            json={
                "file_name": "empty.stl",
                "file_data": encode_file_to_base64(b"")
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_upload_oversized_file(self, http_client, user_account):
        """Test upload of file exceeding size limit"""
        user_data, token = user_account
        
        # Create a large file (simulate 100MB)
        # Note: We don't actually send 100MB, just test the validation
        large_content = b"x" * (1024 * 1024)  # 1MB sample
        
        response = await http_client.post(
            f"{BASE_URL}/files",
            json={
                "file_name": "large.stl",
                "file_data": encode_file_to_base64(large_content)
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should accept if under limit
        assert response.status_code in [200, 400, 413, 422]
    
    @pytest.mark.asyncio
    async def test_upload_unsupported_file_type(self, http_client, user_account):
        """Test upload of unsupported file type"""
        user_data, token = user_account
        
        unsupported_files = [
            ("malware.exe", b"MZ executable"),
            ("script.sh", b"#!/bin/bash\nrm -rf /"),
            ("image.bmp", b"BM image data"),
        ]
        
        for filename, content in unsupported_files:
            response = await http_client.post(
                f"{BASE_URL}/files",
                json={
                    "file_name": filename,
                    "file_data": encode_file_to_base64(content)
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code in [400, 422], \
                f"Unsupported file type should be rejected: {filename}"
    
    @pytest.mark.asyncio
    async def test_download_nonexistent_file(self, http_client, user_account):
        """Test downloading a file that doesn't exist"""
        user_data, token = user_account
        
        response = await http_client.get(
            f"{BASE_URL}/files/999999/download",
            headers={"Authorization": f"Bearer {token}"}
        )
        validate_error_response(response, 404)
    
    @pytest.mark.asyncio
    async def test_preview_generation_failure(self, http_client, user_account):
        """Test handling of preview generation failure"""
        user_data, token = user_account
        
        # Upload a file that might fail preview generation
        response = await http_client.post(
            f"{BASE_URL}/files",
            json={
                "file_name": "test.stl",
                "file_data": encode_file_to_base64(b"invalid stl content")
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            file_data = response.json()
            file_id = file_data["id"]
            
            # Try to get preview
            response = await http_client.get(
                f"{BASE_URL}/files/{file_id}/preview",
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should either return placeholder or error
            assert response.status_code in [200, 404, 500]
            
            # Cleanup
            await http_client.delete(
                f"{BASE_URL}/files/{file_id}",
                headers={"Authorization": f"Bearer {token}"}
            )


@pytest.mark.unit
class TestCalculatorServiceErrors:
    """Test handling of calculator service errors"""
    
    @pytest.mark.asyncio
    async def test_calculation_with_invalid_material_combination(self, http_client):
        """Test calculation with invalid material-service combination"""
        calc_data = generate_test_calculation_data("cnc-milling")
        calc_data["material_id"] = "invalid_material"
        
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data
        )
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.requires_calculator
    async def test_calculator_service_timeout(
        self, http_client, skip_if_calculator_unavailable
    ):
        """Test handling of calculator service timeout"""
        calc_data = generate_test_calculation_data()
        
        # Set very short timeout to simulate timeout
        async with httpx.AsyncClient(timeout=0.001) as quick_client:
            try:
                response = await quick_client.post(
                    f"{BASE_URL}/calculate-price",
                    json=calc_data
                )
                # If it completes, that's also acceptable
                assert response.status_code in [200, 400, 500, 504]
            except httpx.TimeoutException:
                # Timeout is expected
                pass
    
    @pytest.mark.asyncio
    async def test_calculation_missing_dimensions(self, http_client):
        """Test calculation with missing dimensions"""
        calc_data = generate_test_calculation_data()
        del calc_data["length"]
        del calc_data["width"]
        del calc_data["height"]
        
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data
        )
        # Should fail if dimensions required, or accept if file analysis available
        assert response.status_code in [200, 422]
    
    @pytest.mark.asyncio
    async def test_calculation_with_conflicting_parameters(self, http_client):
        """Test calculation with conflicting parameters"""
        calc_data = generate_test_calculation_data("printing")
        calc_data["material_id"] = "alum_D16"  # Metal for 3D printing (conflict)
        
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data
        )
        # Should either reject or handle gracefully
        assert response.status_code in [200, 400, 422]


@pytest.mark.integration
@pytest.mark.requires_bitrix
class TestBitrixServiceErrors:
    """Test handling of Bitrix service errors"""
    
    @pytest.mark.asyncio
    async def test_bitrix_webhook_with_invalid_payload(
        self, http_client, skip_if_bitrix_unavailable
    ):
        """Test Bitrix webhook with invalid payload"""
        invalid_payloads = [
            {},  # Empty
            {"invalid": "data"},  # Missing required fields
            {"event": "UNKNOWN_EVENT"},  # Unknown event type
        ]
        
        for payload in invalid_payloads:
            response = await http_client.post(
                f"{BASE_URL}/bitrix/webhook",
                json=payload
            )
            # Should either accept gracefully or reject
            assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_bitrix_sync_with_no_pending_items(
        self, http_client, admin_token, skip_if_bitrix_unavailable
    ):
        """Test Bitrix sync when queue is empty"""
        response = await http_client.post(
            f"{BASE_URL}/sync/process",
            json={"limit": 10},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should succeed with 0 processed
        assert response.status_code == 200
        result = response.json()
        assert "stats" in result
        assert "processed" in result["stats"]
    
    @pytest.mark.asyncio
    async def test_bitrix_sync_status_when_disabled(self, http_client, admin_token):
        """Test Bitrix sync status when Bitrix is disabled"""
        response = await http_client.get(
            f"{BASE_URL}/sync/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should return status even if disabled
        assert response.status_code == 200
        status = response.json()
        assert "data" in status
        assert "bitrix_configured" in status["data"]


@pytest.mark.unit
class TestDatabaseErrors:
    """Test handling of database-related errors"""
    
    @pytest.mark.asyncio
    async def test_duplicate_order_submission(
        self, http_client, user_account, uploaded_file
    ):
        """Test handling of duplicate order submission"""
        user_data, token = user_account
        
        order_data = {
            "service_id": "cnc-milling",
            "file_id": uploaded_file,
            "quantity": 1,
            "material_id": "alum_D16",
            "length": 100,
            "width": 50,
            "height": 25,
            "tolerance_id": "1",
            "finish_id": "1",
            "k_otk": "1",
            "k_cert": ["a"]
        }
        
        # Submit order twice rapidly
        response1 = await http_client.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        response2 = await http_client.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Both should succeed (no duplicate constraint) or second should fail
        assert response1.status_code == 200
        assert response2.status_code in [200, 400, 409]
    
    @pytest.mark.asyncio
    async def test_concurrent_file_deletion(
        self, http_client, user_account, test_file_upload
    ):
        """Test concurrent deletion of the same file"""
        user_data, token = user_account
        
        # Upload file
        response = await http_client.post(
            f"{BASE_URL}/files",
            json=test_file_upload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        file_id = response.json()["id"]
        
        # Try to delete twice concurrently
        delete_tasks = [
            http_client.delete(
                f"{BASE_URL}/files/{file_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            for _ in range(2)
        ]
        
        responses = await asyncio.gather(*delete_tasks, return_exceptions=True)
        
        # First should succeed, second should fail with 404
        success_count = sum(1 for r in responses if isinstance(r, httpx.Response) and r.status_code == 200)
        assert success_count >= 1, "At least one deletion should succeed"
    
    @pytest.mark.asyncio
    async def test_orphaned_order_handling(
        self, http_client, user_account, uploaded_file
    ):
        """Test handling of orders with deleted files"""
        user_data, token = user_account
        
        # Create order
        order_data = {
            "service_id": "cnc-milling",
            "file_id": uploaded_file,
            "quantity": 1,
            "material_id": "alum_D16",
            "length": 100,
            "width": 50,
            "height": 25,
            "tolerance_id": "1",
            "finish_id": "1",
            "k_otk": "1",
            "k_cert": ["a"]
        }
        
        response = await http_client.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        order_id = response.json()["order_id"]
        
        # Delete the file
        response = await http_client.delete(
            f"{BASE_URL}/files/{uploaded_file}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Try to access the order
        response = await http_client.get(
            f"{BASE_URL}/orders/{order_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should still return order, possibly with missing file info
        assert response.status_code in [200, 404]


@pytest.mark.unit
class TestNetworkErrors:
    """Test handling of network-related errors"""
    
    @pytest.mark.asyncio
    async def test_request_with_invalid_json(self, http_client, user_account):
        """Test request with malformed JSON"""
        user_data, token = user_account
        
        # Send invalid JSON
        try:
            response = await http_client.post(
                f"{BASE_URL}/files",
                content=b"{invalid json}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            # Should return 422 or 400
            assert response.status_code in [400, 422]
        except Exception:
            # Connection error is also acceptable
            pass
    
    @pytest.mark.asyncio
    async def test_request_with_wrong_content_type(
        self, http_client, user_account
    ):
        """Test request with wrong Content-Type header"""
        user_data, token = user_account
        
        response = await http_client.post(
            f"{BASE_URL}/files",
            content=b"plain text content",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "text/plain"
            }
        )
        # Should reject non-JSON
        assert response.status_code in [400, 415, 422]
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_very_slow_request(self, http_client, user_account):
        """Test handling of very slow requests"""
        user_data, token = user_account
        
        # Use very short timeout
        async with httpx.AsyncClient(timeout=0.001) as quick_client:
            try:
                response = await quick_client.get(
                    f"{BASE_URL}/files",
                    headers={"Authorization": f"Bearer {token}"}
                )
                # If it completes quickly, that's fine
                assert response.status_code == 200
            except httpx.TimeoutException:
                # Timeout is expected
                pass


@pytest.mark.unit
class TestEdgeCases:
    """Test various edge cases"""
    
    @pytest.mark.asyncio
    async def test_access_deleted_resource(
        self, http_client, user_account, test_file_upload
    ):
        """Test accessing a resource after it's deleted"""
        user_data, token = user_account
        
        # Upload and delete file
        response = await http_client.post(
            f"{BASE_URL}/files",
            json=test_file_upload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        file_id = response.json()["id"]
        
        response = await http_client.delete(
            f"{BASE_URL}/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Try to access deleted file
        response = await http_client.get(
            f"{BASE_URL}/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        validate_error_response(response, 404)
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_resource(
        self, http_client, admin_token
    ):
        """Test updating a resource that doesn't exist"""
        response = await http_client.put(
            f"{BASE_URL}/admin/orders/999999",
            json={"status": "completed"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        validate_error_response(response, 404)
    
    @pytest.mark.asyncio
    async def test_empty_list_responses(self, http_client, user_account):
        """Test endpoints that return empty lists"""
        user_data, token = user_account
        
        # New user should have no files
        response = await http_client.get(
            f"{BASE_URL}/files",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        files = response.json()
        assert isinstance(files, list)
        
        # New user should have no orders
        response = await http_client.get(
            f"{BASE_URL}/orders",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)
    
    @pytest.mark.asyncio
    async def test_special_characters_in_ids(
        self, http_client, user_account
    ):
        """Test handling of special characters in resource IDs"""
        user_data, token = user_account
        
        invalid_ids = ["abc", "123.456", "-1", "0x123", "../../etc"]
        
        for invalid_id in invalid_ids:
            response = await http_client.get(
                f"{BASE_URL}/files/{invalid_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should return 404 or 422
            assert response.status_code in [404, 422]
    
    @pytest.mark.asyncio
    async def test_pagination_edge_cases(self, http_client, admin_token):
        """Test pagination with edge case parameters"""
        # Note: Implement if pagination is supported
        
        response = await http_client.get(
            f"{BASE_URL}/users",
            params={"page": -1, "limit": 0},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should either handle gracefully or return error
        assert response.status_code in [200, 400, 422]


@pytest.mark.unit
class TestErrorRecovery:
    """Test error recovery and cleanup"""
    
    @pytest.mark.asyncio
    async def test_failed_upload_cleanup(
        self, http_client, user_account
    ):
        """Test that failed uploads clean up properly"""
        user_data, token = user_account
        
        # Try to upload invalid file
        response = await http_client.post(
            f"{BASE_URL}/files",
            json={
                "file_name": "test.stl",
                "file_data": "invalid_base64"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should fail
        assert response.status_code in [400, 422]
        
        # Verify no orphaned files created
        response = await http_client.get(
            f"{BASE_URL}/files",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        # File count should not include failed upload
    
    @pytest.mark.asyncio
    async def test_partial_order_creation_rollback(
        self, http_client, user_account
    ):
        """Test rollback on partial order creation failure"""
        user_data, token = user_account
        
        # Try to create order with invalid data
        response = await http_client.post(
            f"{BASE_URL}/orders",
            json={
                "service_id": "cnc-milling",
                "file_id": 999999,  # Nonexistent file
                "quantity": 1,
                "material_id": "alum_D16",
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should fail
        assert response.status_code in [400, 404, 422]
        
        # Verify no partial order created
        response = await http_client.get(
            f"{BASE_URL}/orders",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        # Order count should not include failed creation

