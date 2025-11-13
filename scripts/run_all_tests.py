"""
Test runner script for all modular API tests
Runs all test suites and provides comprehensive reporting
"""
import asyncio
import sys
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.test_api_comprehensive import ModularAPITester
from tests.test_auth_endpoints import AuthEndpointTester
from tests.test_calculations_endpoints import CalculationsEndpointTester
from tests.test_files_endpoints import FilesEndpointTester
from tests.test_orders_endpoints import OrdersEndpointTester

class TestRunner:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    async def run_test_suite(self, test_class, test_name: str):
        """Run a single test suite"""
        print(f"\n{'='*60}")
        print(f"Running {test_name}")
        print(f"{'='*60}")
        
        start_time = time.time()
        try:
            async with test_class(self.base_url) as tester:
                await tester.run_all_tests()
            end_time = time.time()
            duration = end_time - start_time
            self.results[test_name] = {
                "status": "PASSED",
                "duration": duration
            }
            print(f"\n{test_name} completed successfully in {duration:.2f}s")
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            self.results[test_name] = {
                "status": "FAILED",
                "duration": duration,
                "error": str(e)
            }
            print(f"\n{test_name} failed after {duration:.2f}s: {e}")
    
    async def run_all_tests(self):
        """Run all test suites"""
        print("Starting comprehensive modular API test suite...")
        print(f"Testing against: {self.base_url}")
        
        self.start_time = time.time()
        
        # Define test suites
        test_suites = [
            (ModularAPITester, "Comprehensive API Tests"),
            (AuthEndpointTester, "Authentication Endpoints"),
            (CalculationsEndpointTester, "Calculations Endpoints"),
            (FilesEndpointTester, "Files Endpoints"),
            (OrdersEndpointTester, "Orders Endpoints"),
        ]
        
        # Run each test suite
        for test_class, test_name in test_suites:
            await self.run_test_suite(test_class, test_name)
        
        self.end_time = time.time()
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        if self.start_time and self.end_time:
            total_duration = self.end_time - self.start_time
        else:
            total_duration = 0
        
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        passed = 0
        failed = 0
        
        for test_name, result in self.results.items():
            status = result["status"]
            duration = result["duration"]
            
            if status == "PASSED":
                passed += 1
                print(f"PASSED {test_name:<30} {duration:>8.2f}s")
            else:
                failed += 1
                print(f"FAILED {test_name:<30} {duration:>8.2f}s - {result.get('error', 'Unknown error')}")
        
        print(f"{'='*60}")
        print(f"Total Tests: {passed + failed}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"{'='*60}")
        
        if failed == 0:
            print("All tests passed! The modular API is working correctly.")
        else:
            print(f"{failed} test suite(s) failed. Please check the errors above.")
            sys.exit(1)


async def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run modular API tests")
    parser.add_argument(
        "--url", 
        default="http://localhost:8000",
        help="Base URL for the API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--suite",
        choices=["all", "comprehensive", "auth", "calculations", "files", "orders"],
        default="all",
        help="Test suite to run (default: all)"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner(args.url)
    
    if args.suite == "all":
        await runner.run_all_tests()
    else:
        # Run specific test suite
        test_suites = {
            "comprehensive": (ModularAPITester, "Comprehensive API Tests"),
            "auth": (AuthEndpointTester, "Authentication Endpoints"),
            "calculations": (CalculationsEndpointTester, "Calculations Endpoints"),
            "files": (FilesEndpointTester, "Files Endpoints"),
            "orders": (OrdersEndpointTester, "Orders Endpoints"),
        }
        
        if args.suite in test_suites:
            test_class, test_name = test_suites[args.suite]
            await runner.run_test_suite(test_class, test_name)
            runner.print_summary()
        else:
            print(f"❌ Unknown test suite: {args.suite}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
