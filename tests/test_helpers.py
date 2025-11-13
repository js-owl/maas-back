"""
Test helper utilities
Provides shared utilities, mock builders, service health checkers, and assertion helpers
"""
import asyncio
import httpx
import base64
import time
import json
import os
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
import uuid

from tests.test_config import (
    BASE_URL,
    CALCULATOR_URL,
    BITRIX_WEBHOOK_URL,
    DEFAULT_TIMEOUT,
    QUICK_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    MOCK_CALCULATOR_RESPONSE,
    MOCK_BITRIX_DEAL_RESPONSE,
)


# ============================================================================
# Service Health Checkers
# ============================================================================

async def is_calculator_available() -> bool:
    """Check if calculator service is available on port 7000"""
    try:
        async with httpx.AsyncClient(timeout=QUICK_TIMEOUT) as client:
            response = await client.get(f"{CALCULATOR_URL}/health")
            return response.status_code == 200
    except Exception:
        return False


async def is_bitrix_available() -> bool:
    """Check if Bitrix API is available"""
    if not BITRIX_WEBHOOK_URL:
        return False
    try:
        # Use the same SSL verification setting as the Bitrix client
        import os
        verify_tls = os.getenv("BITRIX_VERIFY_TLS", "true").lower() != "false"
        async with httpx.AsyncClient(timeout=QUICK_TIMEOUT, verify=verify_tls) as client:
            # Try a simple test call
            response = await client.post(
                f"{BITRIX_WEBHOOK_URL}/crm.deal.list",
                json={"select": ["ID"], "filter": {}, "start": 0}
            )
            return response.status_code in [200, 401, 403]  # Service is up even if unauthorized
    except Exception:
        return False


async def is_backend_available() -> bool:
    """Check if backend service is available"""
    try:
        async with httpx.AsyncClient(timeout=QUICK_TIMEOUT) as client:
            response = await client.get(f"{BASE_URL}/health")
            return response.status_code == 200
    except Exception:
        return False


async def wait_for_service(
    check_func: Callable,
    timeout: int = 30,
    interval: int = 1
) -> bool:
    """Wait for a service to become available"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if await check_func():
            return True
        await asyncio.sleep(interval)
    return False


# ============================================================================
# Test Data Generators
# ============================================================================

def generate_unique_username(prefix: str = "test_user") -> str:
    """Generate unique username with timestamp and UUID"""
    timestamp = int(time.time())
    short_uuid = str(uuid.uuid4())[:8]
    return f"{prefix}_{timestamp}_{short_uuid}"


def generate_test_user(user_type: str = "individual") -> Dict[str, str]:
    """Generate test user data"""
    username = generate_unique_username()
    return {
        "username": username,
        "email": f"{username}@test.com",
        "password": "TestPass123!",
        "full_name": f"Test User {username}",
        "phone": "+1234567890",
        "user_type": user_type,
    }


def generate_test_order_data(
    service_id: str = "cnc-milling",
    file_id: Optional[int] = None
) -> Dict[str, Any]:
    """Generate test order data"""
    return {
        "service_id": service_id,
        "file_id": file_id or 1,
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
        "material_id": "alum_D16",
        "material_form": "rod",
        "special_instructions": "Test order",
    }


def generate_test_calculation_data(service_id: str = "cnc-milling") -> Dict[str, Any]:
    """Generate test calculation data"""
    return {
        "service_id": service_id,
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


def create_test_stl_content() -> bytes:
    """Create a simple valid STL file content"""
    # Simple triangle STL file
    stl_content = b"solid test\n"
    stl_content += b"  facet normal 0 0 1\n"
    stl_content += b"    outer loop\n"
    stl_content += b"      vertex 0 0 0\n"
    stl_content += b"      vertex 10 0 0\n"
    stl_content += b"      vertex 5 10 0\n"
    stl_content += b"    endloop\n"
    stl_content += b"  endfacet\n"
    stl_content += b"endsolid test\n"
    return stl_content


def encode_file_to_base64(file_content: bytes) -> str:
    """Encode file content to base64 string"""
    return base64.b64encode(file_content).decode('utf-8')


def generate_test_file_upload() -> Dict[str, str]:
    """Generate test file upload data"""
    stl_content = create_test_stl_content()
    return {
        "file_name": f"test_model_{int(time.time())}.stl",
        "file_data": encode_file_to_base64(stl_content),
        "file_type": "stl",
        "description": "Test STL file",
    }


def generate_test_document_upload() -> Dict[str, str]:
    """Generate test document upload data"""
    pdf_content = b"%PDF-1.4\nTest document content\n%%EOF"
    return {
        "document_name": f"test_doc_{int(time.time())}.pdf",
        "document_data": encode_file_to_base64(pdf_content),
        "document_category": "technical_spec",
    }


# ============================================================================
# Mock Builders
# ============================================================================

def mock_calculator_response(
    service_id: str = "cnc-milling",
    total_price: float = 150.50,
    **kwargs
) -> Dict[str, Any]:
    """Build mock calculator response"""
    response = MOCK_CALCULATOR_RESPONSE.copy()
    response["service_id"] = service_id
    response["total_price"] = total_price
    response.update(kwargs)
    return response


def mock_bitrix_deal_response(
    deal_id: str = "12345",
    title: str = "Test Deal",
    **kwargs
) -> Dict[str, Any]:
    """Build mock Bitrix deal response"""
    response = MOCK_BITRIX_DEAL_RESPONSE.copy()
    response["result"]["id"] = deal_id
    response["result"]["title"] = title
    if kwargs:
        response["result"].update(kwargs)
    return response


def mock_bitrix_webhook(
    event: str = "ONCRMDEALUPDATE",
    entity_id: str = "12345",
    **kwargs
) -> Dict[str, Any]:
    """Build mock Bitrix webhook payload"""
    return {
        "event": event,
        "data": {
            "FIELDS": {
                "ID": entity_id,
                **kwargs
            }
        },
        "ts": str(int(time.time())),
        "auth": {
            "domain": "test.bitrix24.com",
            "application_token": "test_token"
        }
    }


# ============================================================================
# Assertion Helpers
# ============================================================================

def assert_response_schema(
    response: Dict[str, Any],
    required_fields: List[str],
    optional_fields: Optional[List[str]] = None
) -> None:
    """Assert response contains required fields"""
    for field in required_fields:
        assert field in response, f"Required field '{field}' missing from response"
    
    if optional_fields:
        all_fields = set(required_fields + optional_fields)
        for field in response.keys():
            assert field in all_fields, f"Unexpected field '{field}' in response"


def assert_user_schema(user: Dict[str, Any]) -> None:
    """Assert user object has correct schema"""
    required_fields = ["id", "username", "email", "user_type", "created_at"]
    assert_response_schema(user, required_fields)


def assert_file_schema(file: Dict[str, Any]) -> None:
    """Assert file object has correct schema"""
    required_fields = ["id", "filename", "original_filename", "file_size", "file_type", "uploaded_at"]
    assert_response_schema(file, required_fields)


def assert_order_schema(order: Dict[str, Any]) -> None:
    """Assert order object has correct schema"""
    required_fields = ["order_id", "user_id", "service_id", "status", "total_price", "created_at"]
    assert_response_schema(order, required_fields)


def assert_calculation_schema(calculation: Dict[str, Any]) -> None:
    """Assert calculation response has correct schema"""
    required_fields = ["service_id", "total_price", "detail_price", "mat_price", "work_price"]
    assert_response_schema(calculation, required_fields)


async def assert_file_exists(file_path: str) -> None:
    """Assert file exists on filesystem"""
    assert os.path.exists(file_path), f"File does not exist: {file_path}"


async def assert_file_not_exists(file_path: str) -> None:
    """Assert file does not exist on filesystem"""
    assert not os.path.exists(file_path), f"File should not exist: {file_path}"


# ============================================================================
# Cleanup Utilities
# ============================================================================

async def cleanup_test_user(
    client: httpx.AsyncClient,
    base_url: str,
    username: str,
    admin_token: str
) -> None:
    """Clean up test user (admin operation)"""
    try:
        # Get user by username
        response = await client.get(
            f"{base_url}/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200:
            users = response.json()
            for user in users:
                if user.get("username") == username:
                    # Delete user
                    await client.delete(
                        f"{base_url}/users/{user['id']}",
                        headers={"Authorization": f"Bearer {admin_token}"}
                    )
                    break
    except Exception as e:
        print(f"Warning: Failed to cleanup user {username}: {e}")


async def cleanup_test_file(
    client: httpx.AsyncClient,
    base_url: str,
    file_id: int,
    auth_token: str
) -> None:
    """Clean up test file"""
    try:
        await client.delete(
            f"{base_url}/files/{file_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    except Exception as e:
        print(f"Warning: Failed to cleanup file {file_id}: {e}")


async def cleanup_test_order(
    client: httpx.AsyncClient,
    base_url: str,
    order_id: int,
    admin_token: str
) -> None:
    """Clean up test order (admin operation)"""
    try:
        await client.delete(
            f"{base_url}/admin/orders/{order_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    except Exception as e:
        print(f"Warning: Failed to cleanup order {order_id}: {e}")


async def cleanup_uploads_directory() -> None:
    """Clean up test uploads directory"""
    try:
        test_uploads = Path("uploads/test")
        if test_uploads.exists():
            for file in test_uploads.glob("*"):
                if file.is_file():
                    file.unlink()
    except Exception as e:
        print(f"Warning: Failed to cleanup uploads: {e}")


# ============================================================================
# Retry Utilities
# ============================================================================

async def retry_async(
    func: Callable,
    max_retries: int = MAX_RETRIES,
    delay: float = RETRY_DELAY_SECONDS,
    exceptions: tuple = (Exception,)
) -> Any:
    """Retry async function on failure"""
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries - 1:
                await asyncio.sleep(delay * (attempt + 1))  # Exponential backoff
            continue
    raise last_exception


# ============================================================================
# Authentication Helpers
# ============================================================================

async def login_user(
    client: httpx.AsyncClient,
    base_url: str,
    username: str,
    password: str
) -> str:
    """Login user and return access token"""
    response = await client.post(
        f"{base_url}/login",
        json={"username": username, "password": password}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


async def register_and_login(
    client: httpx.AsyncClient,
    base_url: str,
    user_type: str = "individual"
) -> tuple[Dict[str, str], str]:
    """Register a new user and login, return user data and token"""
    user_data = generate_test_user(user_type)
    
    # Register
    response = await client.post(f"{base_url}/register", json=user_data)
    assert response.status_code == 200, f"Registration failed: {response.text}"
    
    # Login
    token = await login_user(client, base_url, user_data["username"], user_data["password"])
    
    return user_data, token


# ============================================================================
# Response Validators
# ============================================================================

def validate_error_response(
    response: httpx.Response,
    expected_status: int,
    expected_error: Optional[str] = None
) -> None:
    """Validate error response structure"""
    assert response.status_code == expected_status, \
        f"Expected status {expected_status}, got {response.status_code}: {response.text}"
    
    if expected_error:
        error_data = response.json()
        assert "error" in error_data or "detail" in error_data or "message" in error_data, \
            f"No error message in response: {response.text}"


def validate_success_response(
    response: httpx.Response,
    expected_status: int = 200
) -> Dict[str, Any]:
    """Validate success response and return JSON"""
    assert response.status_code == expected_status, \
        f"Expected status {expected_status}, got {response.status_code}: {response.text}"
    return response.json()

