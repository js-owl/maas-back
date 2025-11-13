# Quick Start Guide - Comprehensive Testing

## Prerequisites

1. **Start the backend server:**
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start calculator service (for integration tests):**
   ```bash
   # In the stl/ directory
   uvicorn main:app --reload --host 0.0.0.0 --port 7000
   ```

3. **Install test dependencies:**
   ```bash
   pip install pytest pytest-asyncio pytest-cov httpx
   ```

## Quick Commands

### Run All Fast Tests (Recommended for Development)
```bash
python scripts/run_pytest_tests.py --mode unit
```
⏱️ ~30 seconds | 🧪 ~90 tests | ✅ All external services mocked

### Run All Tests with Real Services
```bash
python scripts/run_pytest_tests.py --mode all
```
⏱️ ~5 minutes | 🧪 ~175 tests | 🔗 Requires calculator + Bitrix

### Run Security Tests
```bash
python scripts/run_pytest_tests.py --category security
```
⏱️ ~10 seconds | 🧪 ~30 tests | 🔒 Security validation

### Run with Coverage Report
```bash
python scripts/run_pytest_tests.py --mode unit --coverage
```
⏱️ ~40 seconds | 🧪 ~90 tests | 📊 HTML coverage report generated

### Run Tests in Parallel (Fastest)
```bash
python scripts/run_pytest_tests.py --mode unit --parallel 4
```
⏱️ ~10 seconds | 🧪 ~90 tests | ⚡ 4x faster execution

## Test Modes Explained

| Mode | Speed | Services | Use Case |
|------|-------|----------|----------|
| `unit` | Fast (~30s) | Mocked | CI/CD, development |
| `integration` | Medium (~2min) | Real | Pre-deployment validation |
| `e2e` | Slow (~3min) | Real | Staging/production readiness |
| `all` | Full (~5min) | Mixed | Complete validation |

## Test Categories

| Category | Tests | Focus |
|----------|-------|-------|
| `security` | ~30 | Auth, injection, authorization |
| `validation` | ~25 | Schema, types, boundaries |
| `error` | ~40 | Edge cases, failures |
| `workflow` | ~30 | E2E user journeys |
| `service` | ~10 | Calculator + Bitrix integration |

## Common Scenarios

### Before Committing Code
```bash
# Fast feedback (30 seconds)
python scripts/run_pytest_tests.py --mode unit --failfast
```

### Before Creating Pull Request
```bash
# Full validation with coverage
python scripts/run_pytest_tests.py --mode all --coverage
```

### Testing New Feature
```bash
# Run specific test file
pytest tests/test_security_validation.py -v
```

### Debugging Failed Test
```bash
# Run single test with full output
pytest tests/test_security_validation.py::TestAuthenticationSecurity::test_missing_token_returns_401 -v -s
```

### Check Integration Points
```bash
# Test calculator + Bitrix integration
python scripts/run_pytest_tests.py --mode integration
```

## Environment Variables

Set these in your `.env` file or shell:

```bash
# Required
export TEST_BASE_URL="http://localhost:8000"
export CALCULATOR_BASE_URL="http://localhost:7000"

# Optional (for Bitrix integration tests)
export BITRIX_WEBHOOK_URL="https://your-domain.bitrix24.com/rest/..."

# Optional (admin credentials)
export TEST_ADMIN_USERNAME="admin"
export TEST_ADMIN_PASSWORD="admin123"
```

## Interpreting Results

### ✅ PASSED
Test completed successfully. No action needed.

### ⚠️ SKIPPED
Service unavailable (e.g., calculator not running). 
- Unit tests: OK (services mocked)
- Integration tests: Start required services

### ❌ FAILED
Test failed. Check error message for details:
1. Read the assertion error
2. Check the test file for expected behavior
3. Verify service availability
4. Check test configuration

## Coverage Report

After running with `--coverage`:

1. **Terminal output**: Summary with missing lines
2. **HTML report**: Open `htmlcov/index.html` in browser
3. **Target**: Aim for 80%+ coverage

## Troubleshooting

### "Calculator service unavailable"
```bash
# Start calculator service
cd stl/
uvicorn main:app --reload --port 7000
```

### "Admin login failed"
```bash
# Check admin credentials
export TEST_ADMIN_USERNAME="admin"
export TEST_ADMIN_PASSWORD="admin123"
```

### "Tests hanging"
```bash
# Check backend is running
curl http://localhost:8000/health
```

### "Permission denied on cleanup"
```bash
# Clear test uploads
rm -rf uploads/test/*
```

## Pro Tips

### 1. Run tests on file save (watch mode)
```bash
pip install pytest-watch
ptw tests/ -m unit
```

### 2. Run only failed tests
```bash
pytest --lf  # --last-failed
```

### 3. Run new tests first
```bash
pytest --nf  # --new-first
```

### 4. Get test execution times
```bash
pytest --durations=10  # Show 10 slowest tests
```

### 5. Parallel execution for speed
```bash
pip install pytest-xdist
pytest -n auto  # Use all CPU cores
```

## File Structure Reference

```
tests/
├── pytest.ini                      # Pytest configuration
├── conftest.py                     # Shared fixtures
├── test_config.py                  # Test configuration
├── test_helpers.py                 # Utility functions
│
├── test_security_validation.py     # Security tests (30)
├── test_data_validation.py         # Validation tests (25)
├── test_error_handling.py          # Error tests (40)
├── test_workflows_mocked.py        # Mocked workflows (15)
├── test_workflows_integration.py   # Real workflows (15)
├── test_service_integration.py     # Service integration (10)
│
├── test_auth_endpoints.py          # Existing auth tests
├── test_users_endpoints.py         # Existing user tests
├── test_files_endpoints.py         # Existing file tests
├── test_documents_endpoints.py     # Existing doc tests
├── test_calculations_endpoints.py  # Existing calc tests
├── test_orders_endpoints.py        # Existing order tests
├── test_call_requests_endpoints.py # Existing call tests
├── test_bitrix_endpoints.py        # Existing Bitrix tests
│
├── README.md                       # Comprehensive docs
├── TESTING_IMPLEMENTATION_SUMMARY.md
└── QUICK_START.md                  # This file
```

## Next Steps

1. ✅ Run unit tests to verify setup
2. ✅ Start calculator service for integration tests
3. ✅ Run all tests to ensure complete coverage
4. ✅ Review coverage report for gaps
5. ✅ Integrate into CI/CD pipeline

## Support

For issues or questions:
1. Check `tests/README.md` for detailed documentation
2. Review `tests/TESTING_IMPLEMENTATION_SUMMARY.md` for implementation details
3. Check test file docstrings for specific test behavior
4. Review `tests/test_config.py` for configuration options

---

**Happy Testing! 🧪✨**

