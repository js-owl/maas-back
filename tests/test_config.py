"""
Test configuration and constants
Centralizes all test settings, URLs, timeouts, and service configuration
"""
import os
from typing import Dict, Any

# Base URLs
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
CALCULATOR_URL = os.getenv("CALCULATOR_BASE_URL", "http://localhost:7000")
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL") or os.getenv("BITRIX24_WEBHOOK_URL", "")

# Timeouts (in seconds)
DEFAULT_TIMEOUT = 30.0
QUICK_TIMEOUT = 10.0
LONG_TIMEOUT = 60.0
UPLOAD_TIMEOUT = 120.0

# Test data paths
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data")
TEST_UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "test")
TEST_FILES_DIR = os.path.join(TEST_DATA_DIR, "files")

# Test user credentials
TEST_USER_PREFIX = "test_user"
TEST_ADMIN_USERNAME = os.getenv("TEST_ADMIN_USERNAME", "admin")
TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin123")

# File size limits for testing
MAX_FILE_SIZE_MB = 50
TEST_SMALL_FILE_SIZE = 1024  # 1KB
TEST_MEDIUM_FILE_SIZE = 1024 * 1024  # 1MB
TEST_LARGE_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Service availability
CHECK_CALCULATOR_SERVICE = True
CHECK_BITRIX_SERVICE = True
SKIP_ON_SERVICE_UNAVAILABLE = True

# Test execution settings
ENABLE_CLEANUP = True
CLEANUP_ON_FAILURE = True
PARALLEL_TEST_COUNT = 4

# Performance test settings
PERFORMANCE_MIN_RESPONSE_TIME_MS = 100
PERFORMANCE_MAX_RESPONSE_TIME_MS = 5000
LOAD_TEST_CONCURRENT_USERS = [1, 5, 10, 20]
LOAD_TEST_DURATION_SECONDS = 30

# Retry settings for flaky tests
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1

# Mock data templates
MOCK_CALCULATOR_RESPONSE: Dict[str, Any] = {
    "service_id": "cnc-milling",
    "total_price": 150.50,
    "detail_price": 150.50,
    "mat_price": 75.25,
    "work_price": 75.25,
    "mat_weight": 0.5,
    "mat_volume": 0.000125,
    "total_time": 2.5,
    "manufacturing_cycle": "2-3 days"
}

MOCK_BITRIX_DEAL_RESPONSE: Dict[str, Any] = {
    "result": {
        "id": "12345",
        "title": "Test Deal",
        "stage_id": "NEW",
        "opportunity": "150.50",
        "currency_id": "USD"
    }
}

MOCK_BITRIX_WEBHOOK_PAYLOAD: Dict[str, Any] = {
    "event": "ONCRMDEALUPDATE",
    "data": {
        "FIELDS": {
            "ID": "12345",
            "TITLE": "Test Deal",
            "STAGE_ID": "WON"
        }
    },
    "ts": "1234567890",
    "auth": {
        "domain": "test.bitrix24.com",
        "application_token": "test_token"
    }
}

# Test materials and services
TEST_MATERIALS = {
    "cnc-milling": "alum_D16",
    "cnc-lathe": "steel_45",
    "printing": "PA11",
    "painting": "powder_coating"
}

TEST_SERVICES = ["cnc-milling", "cnc-lathe", "printing", "painting"]

# Validation test data
INVALID_USERNAMES = ["", "a", "a" * 256, "user@invalid", "user name", "<script>alert('xss')</script>"]
INVALID_EMAILS = ["", "notanemail", "@example.com", "user@", "user@.com"]
INVALID_PASSWORDS = ["", "short", "no_upper_case123", "NO_LOWER_CASE123"]

# SQL injection test patterns
SQL_INJECTION_PATTERNS = [
    "'; DROP TABLE users; --",
    "1' OR '1'='1",
    "admin'--",
    "1; DELETE FROM orders WHERE '1'='1",
]

# XSS test patterns
XSS_PATTERNS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert('XSS')>",
    "javascript:alert('XSS')",
    "<svg onload=alert('XSS')>",
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32\\config\\sam",
    "....//....//....//etc/passwd",
]

def get_test_config() -> Dict[str, Any]:
    """Get complete test configuration as dictionary"""
    return {
        "base_url": BASE_URL,
        "calculator_url": CALCULATOR_URL,
        "bitrix_webhook_url": BITRIX_WEBHOOK_URL,
        "timeouts": {
            "default": DEFAULT_TIMEOUT,
            "quick": QUICK_TIMEOUT,
            "long": LONG_TIMEOUT,
            "upload": UPLOAD_TIMEOUT,
        },
        "service_checks": {
            "calculator": CHECK_CALCULATOR_SERVICE,
            "bitrix": CHECK_BITRIX_SERVICE,
            "skip_on_unavailable": SKIP_ON_SERVICE_UNAVAILABLE,
        },
        "cleanup": {
            "enable": ENABLE_CLEANUP,
            "on_failure": CLEANUP_ON_FAILURE,
        },
    }

