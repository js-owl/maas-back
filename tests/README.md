# Comprehensive API Test Suite

This directory contains a comprehensive test suite for the MaaS Backend API with **dual testing strategy**: fast unit tests with mocked dependencies AND integration tests with real services.

## Test Architecture

### Dual Testing Strategy

1. **Unit Tests** (Fast, Mocked)
   - All external services mocked (calculator, Bitrix)
   - Fast execution (< 1s per test)
   - Run in CI/CD on every commit
   - Marked with `@pytest.mark.unit`

2. **Integration Tests** (Real Services)
   - Real calculator service (port 7000)
   - Real Bitrix API connectivity
   - Real database interactions
   - Marked with `@pytest.mark.integration`

3. **E2E Tests** (Complete System)
   - Full stack with all services
   - Complete user journeys
   - Marked with `@pytest.mark.e2e`

## Test Files

### Core Endpoint Tests (Existing)
- **`test_api_comprehensive.py`** - Overall API health and system tests
- **`test_auth_endpoints.py`** - Authentication and registration
- **`test_users_endpoints.py`** - User management and profiles
- **`test_files_endpoints.py`** - 3D file upload and management
- **`test_documents_endpoints.py`** - Document management
- **`test_calculations_endpoints.py`** - Price calculations
- **`test_orders_endpoints.py`** - Order creation and management
- **`test_call_requests_endpoints.py`** - Call request workflows
- **`test_bitrix_endpoints.py`** - Bitrix CRM sync operations
- **`test_integration_comprehensive.py`** - End-to-end integration tests

### New Security & Validation Tests
- **`test_security_validation.py`** - Security-focused tests
  - Authentication security (invalid tokens, expired tokens)
  - Authorization bypass attempts
  - Privilege escalation prevention
  - SQL injection prevention
  - XSS prevention
  - Path traversal prevention
  - CORS validation
  - Session security

- **`test_data_validation.py`** - Schema and input validation
  - Required field validation
  - Data type validation
  - Boundary value testing
  - Field length limits
  - Invalid format handling
  - Response schema validation

### New Error Handling Tests
- **`test_error_handling.py`** - Error scenarios and edge cases
  - Invalid file handling (corrupted, empty, oversized)
  - Calculator service errors
  - Bitrix service errors
  - Database errors (race conditions, duplicates)
  - Network errors (timeouts, malformed requests)
  - Resource cleanup and rollback

### New Workflow Tests
- **`test_workflows_mocked.py`** - Fast workflow tests (mocked)
  - Complete user journey (mocked services)
  - Admin oversight workflow (mocked)
  - Error recovery workflow (mocked)
  - Multi-service workflow (mocked)

- **`test_workflows_integration.py`** - Real workflow tests
  - End-to-end order creation with real calculator
  - Bitrix CRM integration workflows
  - Admin oversight with real sync
  - Service availability handling

### New Service Integration Tests
- **`test_service_integration.py`** - Cross-service integration
  - Calculator service integration
  - Bitrix CRM integration
  - Cross-service workflows

## Test Infrastructure

### Configuration Files
- **`pytest.ini`** - Pytest configuration with markers
- **`conftest.py`** - Shared fixtures and test setup
- **`test_config.py`** - Centralized test configuration
- **`test_helpers.py`** - Utility functions and helpers

### Key Features
- **Service Detection**: Auto-detect calculator and Bitrix availability
- **Smart Skipping**: Skip integration tests if services unavailable
- **Fixtures**: Reusable test data and setup
- **Cleanup**: Automatic cleanup after tests
- **Mocking**: Comprehensive mock builders for external services

## Running Tests

### Prerequisites

1. **Start the backend server:**
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **For integration tests, ensure services are running:**
   - Calculator service on port 7000
   - Bitrix CRM API accessible (if testing Bitrix integration)

3. **Install test dependencies:**
   ```bash
   pip install pytest pytest-asyncio pytest-cov pytest-xdist httpx
   ```

### Using the Enhanced Pytest Runner (Recommended)

#### Run Unit Tests (Fast, Mocked)
```bash
python scripts/run_pytest_tests.py --mode unit
```

#### Run Integration Tests (Real Services)
```bash
python scripts/run_pytest_tests.py --mode integration
```

#### Run All Tests
```bash
python scripts/run_pytest_tests.py --mode all
```

#### Run Specific Categories
```bash
# Security tests only
python scripts/run_pytest_tests.py --category security

# Data validation tests
python scripts/run_pytest_tests.py --category validation

# Error handling tests
python scripts/run_pytest_tests.py --category error

# Workflow tests
python scripts/run_pytest_tests.py --category workflow
```

#### Run with Coverage
```bash
python scripts/run_pytest_tests.py --mode unit --coverage
```

#### Run in Parallel (Faster)
```bash
python scripts/run_pytest_tests.py --mode unit --parallel 4
```

### Using Pytest Directly

#### Run All Unit Tests
```bash
pytest tests/ -m unit -v
```

#### Run All Integration Tests
```bash
pytest tests/ -m integration -v
```

#### Run Specific Test File
```bash
pytest tests/test_security_validation.py -v
```

#### Run Tests Requiring Calculator Service
```bash
pytest tests/ -m requires_calculator -v
```

#### Run Tests Requiring Bitrix Service
```bash
pytest tests/ -m requires_bitrix -v
```

#### Run with Coverage Report
```bash
pytest tests/ --cov=backend --cov-report=html --cov-report=term-missing
```

### Using Legacy Test Runner

For backward compatibility with existing test classes:
```bash
python scripts/run_all_tests.py
python scripts/run_all_tests.py --suite auth
python scripts/run_all_tests.py --suite calculations
```

### Test Configuration

- **Base URL**: `http://localhost:8000` (set via `TEST_BASE_URL` env var)
- **Calculator URL**: `http://localhost:7000` (set via `CALCULATOR_BASE_URL` env var)
- **Bitrix Webhook**: Set via `BITRIX_WEBHOOK_URL` env var
- **Admin Credentials**: Default `admin/admin123` (set via `TEST_ADMIN_USERNAME`, `TEST_ADMIN_PASSWORD`)
- **Timeouts**: Configurable in `tests/test_config.py`

## Test Features

### Comprehensive Coverage
- **Security**: Authorization, authentication, injection prevention
- **Validation**: Schema, data types, boundaries, required fields
- **Error Handling**: Invalid inputs, service failures, edge cases
- **Workflows**: Complete user journeys, admin operations, recovery scenarios
- **Integration**: Real calculator service, Bitrix CRM, cross-service workflows

### Smart Service Detection
- Auto-detects calculator service availability (port 7000)
- Auto-detects Bitrix API connectivity
- Skips integration tests gracefully if services unavailable
- Provides clear warnings for missing services

### Dual Testing Strategy
- **Unit tests**: Fast (<1s), mocked dependencies, run in CI/CD
- **Integration tests**: Real services, thorough validation, run before deployment
- **E2E tests**: Complete system, user journeys, staging validation

### Advanced Features
- **Fixtures**: Reusable test data and setup via pytest fixtures
- **Automatic Cleanup**: Resources cleaned up after tests
- **Parallel Execution**: Run tests in parallel for speed
- **Coverage Reporting**: Track code coverage with pytest-cov
- **Performance Timing**: Track test execution time

## Test Results Format

Tests provide detailed output:
- ✅ **PASSED**: Test completed successfully
- ⚠️ **SKIPPED**: Service unavailable, test skipped
- ❌ **FAILED**: Test failed with detailed error
- 📊 **SUMMARY**: Overall statistics (passed/failed/skipped)
- ⏱️ **TIMING**: Execution time for each test
- 📈 **COVERAGE**: Code coverage percentage (with --coverage flag)

## Expected Test Counts

### Unit Tests (Fast)
- Security validation: ~30 tests
- Data validation: ~25 tests
- Error handling: ~20 tests (mocked)
- Workflows (mocked): ~15 tests
- **Total**: ~90 new unit tests

### Integration Tests (Real Services)
- Workflow integration: ~15 tests
- Service integration: ~20 tests
- **Total**: ~35 integration tests

### Existing Tests
- 10 existing test files with ~50-60 tests
- **Grand Total**: 175+ comprehensive tests

## Best Practices

### Writing New Tests
1. Use pytest fixtures from `conftest.py`
2. Mark tests appropriately (`@pytest.mark.unit`, `@pytest.mark.integration`)
3. Use helpers from `test_helpers.py`
4. Clean up resources in test teardown
5. Use descriptive test names and docstrings

### Test Isolation
- Each test should be independent
- Use unique usernames/IDs (timestamps, UUIDs)
- Clean up created resources
- Don't rely on test execution order

### Service Mocking
- Mock external services in unit tests
- Use real services in integration tests
- Provide clear mock builders in `test_helpers.py`
- Document mock behavior

## Troubleshooting

### Tests Failing
1. **Authentication errors**: Check admin credentials match `TEST_ADMIN_USERNAME/PASSWORD`
2. **Service unavailable**: Ensure backend is running on port 8000
3. **Calculator errors**: Check calculator service on port 7000 (or skip with `--mode unit`)
4. **Bitrix errors**: Check Bitrix webhook URL (or skip integration tests)

### Tests Hanging
1. Check for infinite loops in async code
2. Verify timeout settings in `test_config.py`
3. Use `--timeout` flag with pytest

### Cleanup Issues
1. Manual cleanup: Delete test users from database
2. Clear uploads/test directory
3. Check for orphaned resources

## CI/CD Integration

### Recommended CI Pipeline
```yaml
# Fast feedback loop
- run: pytest tests/ -m unit -v
  
# Integration validation  
- run: pytest tests/ -m integration -v
  if: services_available
  
# E2E validation
- run: pytest tests/ -m e2e -v
  if: staging_environment
```

### Coverage Requirements
- Maintain 80%+ code coverage
- Run coverage checks in CI: `pytest --cov=backend --cov-fail-under=80`

## Notes

- Tests are designed to be independent and can run in any order
- Test data uses unique identifiers to avoid conflicts
- Automatic cleanup prevents test pollution
- Tests handle service unavailability gracefully
- All tests use proper async/await patterns for FastAPI compatibility
- Mock builders ensure consistent test behavior
- Fixtures provide reusable test infrastructure
