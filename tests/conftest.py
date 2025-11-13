"""
Pytest configuration and fixtures
Provides shared fixtures for database, services, mocks, and test data
"""
import pytest
import asyncio
import httpx
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from tests.test_config import (
    BASE_URL,
    CALCULATOR_URL,
    BITRIX_WEBHOOK_URL,
    DEFAULT_TIMEOUT,
    TEST_ADMIN_USERNAME,
    TEST_ADMIN_PASSWORD,
)
from tests.test_helpers import (
    is_calculator_available,
    is_bitrix_available,
    is_backend_available,
    generate_test_user,
    login_user,
    register_and_login,
    mock_calculator_response,
    mock_bitrix_deal_response,
    cleanup_uploads_directory,
)


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: Fast unit tests with mocked dependencies"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests requiring real services"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests with complete system"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and load tests"
    )
    config.addinivalue_line(
        "markers", "security: Security-focused validation tests"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer than 5 seconds"
    )
    config.addinivalue_line(
        "markers", "requires_calculator: Tests requiring calculator service"
    )
    config.addinivalue_line(
        "markers", "requires_bitrix: Tests requiring Bitrix API"
    )


# ============================================================================
# Event Loop Fixture (for async tests)
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Service Availability Fixtures
# ============================================================================

@pytest.fixture(scope="session")
async def backend_available() -> bool:
    """Check if backend service is available"""
    return await is_backend_available()


@pytest.fixture(scope="session")
async def calculator_available() -> bool:
    """Check if calculator service is available"""
    return await is_calculator_available()


@pytest.fixture(scope="session")
async def bitrix_available() -> bool:
    """Check if Bitrix API is available"""
    return await is_bitrix_available()


@pytest.fixture
def skip_if_calculator_unavailable(calculator_available):
    """Skip test if calculator service is not available"""
    if not calculator_available:
        pytest.skip("Calculator service not available")


@pytest.fixture
def skip_if_bitrix_unavailable(bitrix_available):
    """Skip test if Bitrix API is not available"""
    if not bitrix_available:
        pytest.skip("Bitrix API not available")


# ============================================================================
# HTTP Client Fixtures
# ============================================================================

@pytest.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide HTTP client for tests"""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        yield client


@pytest.fixture
async def calculator_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide calculator service HTTP client"""
    async with httpx.AsyncClient(
        base_url=CALCULATOR_URL,
        timeout=DEFAULT_TIMEOUT
    ) as client:
        yield client


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
async def admin_token(http_client) -> str:
    """Get admin authentication token"""
    token = await login_user(
        http_client,
        BASE_URL,
        TEST_ADMIN_USERNAME,
        TEST_ADMIN_PASSWORD
    )
    return token


@pytest.fixture
async def user_account(http_client) -> tuple[Dict[str, str], str]:
    """Create and login a test user, return user data and token"""
    user_data, token = await register_and_login(http_client, BASE_URL, "individual")
    return user_data, token


@pytest.fixture
async def legal_user_account(http_client) -> tuple[Dict[str, str], str]:
    """Create and login a legal entity user, return user data and token"""
    user_data, token = await register_and_login(http_client, BASE_URL, "legal")
    return user_data, token


@pytest.fixture
async def multiple_users(http_client) -> list[tuple[Dict[str, str], str]]:
    """Create multiple test users for concurrent testing"""
    users = []
    for _ in range(3):
        user_data, token = await register_and_login(http_client, BASE_URL)
        users.append((user_data, token))
    return users


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_calculator_service():
    """Mock calculator service responses"""
    with patch('backend.calculations.service.call_calculator_service') as mock_calc:
        mock_calc.return_value = mock_calculator_response()
        yield mock_calc


@pytest.fixture
def mock_bitrix_api():
    """Mock Bitrix API responses"""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_bitrix_deal_response()
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_file_storage():
    """Mock file storage operations"""
    with patch('backend.files.storage.FileStorage') as mock_storage:
        mock_instance = MagicMock()
        mock_instance.save_file.return_value = "/path/to/saved/file.stl"
        mock_instance.delete_file.return_value = True
        mock_instance.get_file_path.return_value = "/path/to/file.stl"
        mock_storage.return_value = mock_instance
        yield mock_storage


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def test_user_data() -> Dict[str, str]:
    """Generate test user data"""
    return generate_test_user("individual")


@pytest.fixture
def test_legal_user_data() -> Dict[str, str]:
    """Generate test legal user data"""
    return generate_test_user("legal")


@pytest.fixture
def test_calculation_data() -> Dict[str, Any]:
    """Generate test calculation data"""
    from tests.test_helpers import generate_test_calculation_data
    return generate_test_calculation_data("cnc-milling")


@pytest.fixture
def test_order_data() -> Dict[str, Any]:
    """Generate test order data"""
    from tests.test_helpers import generate_test_order_data
    return generate_test_order_data("cnc-milling")


@pytest.fixture
def test_file_upload() -> Dict[str, str]:
    """Generate test file upload data"""
    from tests.test_helpers import generate_test_file_upload
    return generate_test_file_upload()


@pytest.fixture
def test_document_upload() -> Dict[str, str]:
    """Generate test document upload data"""
    from tests.test_helpers import generate_test_document_upload
    return generate_test_document_upload()


# ============================================================================
# Resource Management Fixtures
# ============================================================================

@pytest.fixture
async def uploaded_file(http_client, user_account, test_file_upload):
    """Upload a test file and return its ID"""
    user_data, token = user_account
    
    response = await http_client.post(
        f"{BASE_URL}/files",
        json=test_file_upload,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200, f"File upload failed: {response.text}"
    file_data = response.json()
    file_id = file_data["id"]
    
    yield file_id
    
    # Cleanup: delete file after test
    try:
        await http_client.delete(
            f"{BASE_URL}/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
    except Exception as e:
        print(f"Warning: Failed to cleanup file {file_id}: {e}")


@pytest.fixture
async def uploaded_document(http_client, user_account, test_document_upload):
    """Upload a test document and return its ID"""
    user_data, token = user_account
    
    response = await http_client.post(
        f"{BASE_URL}/documents",
        json=test_document_upload,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200, f"Document upload failed: {response.text}"
    doc_data = response.json()
    doc_id = doc_data["id"]
    
    yield doc_id
    
    # Cleanup: delete document after test
    try:
        await http_client.delete(
            f"{BASE_URL}/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
    except Exception as e:
        print(f"Warning: Failed to cleanup document {doc_id}: {e}")


@pytest.fixture
async def created_order(http_client, user_account, uploaded_file, test_order_data):
    """Create a test order and return its ID"""
    user_data, token = user_account
    
    # Update order data with uploaded file
    order_data = test_order_data.copy()
    order_data["file_id"] = uploaded_file
    
    response = await http_client.post(
        f"{BASE_URL}/orders",
        json=order_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200, f"Order creation failed: {response.text}"
    order = response.json()
    order_id = order["order_id"]
    
    yield order_id
    
    # Cleanup handled by cascade delete when user is deleted


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(scope="function", autouse=True)
async def cleanup_after_test():
    """Cleanup after each test"""
    yield
    # Cleanup logic runs after test
    await cleanup_uploads_directory()


@pytest.fixture(scope="session", autouse=True)
async def cleanup_after_session():
    """Cleanup after entire test session"""
    yield
    # Final cleanup
    await cleanup_uploads_directory()


# ============================================================================
# Parametrize Helpers
# ============================================================================

@pytest.fixture(params=["cnc-milling", "cnc-lathe", "printing", "painting"])
def service_id(request):
    """Parametrize tests across all service types"""
    return request.param


@pytest.fixture(params=["individual", "legal"])
def user_type(request):
    """Parametrize tests across user types"""
    return request.param


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def performance_timer():
    """Timer for performance tests"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed_ms(self) -> float:
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return 0
        
        def assert_max_time(self, max_ms: float, message: str = ""):
            elapsed = self.elapsed_ms
            assert elapsed <= max_ms, \
                f"Performance check failed: {elapsed:.2f}ms > {max_ms}ms. {message}"
    
    return Timer()

