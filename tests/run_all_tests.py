#!/usr/bin/env python3
"""
Master test runner for all API endpoints
"""
import asyncio
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_auth_endpoints import AuthEndpointTester as TestAuthEndpoints
from test_users_endpoints import TestUsersEndpoints
from test_files_endpoints import FilesEndpointTester as TestFilesEndpoints
from test_documents_endpoints import TestDocumentsEndpoints
from test_calculations_endpoints import CalculationsEndpointTester as TestCalculationsEndpoints
from test_orders_endpoints import OrdersEndpointTester as TestOrdersEndpoints
from test_call_requests_endpoints import TestCallRequestsEndpoints
from test_bitrix_endpoints import TestBitrixEndpoints
from test_integration_comprehensive import ComprehensiveIntegrationTester as TestIntegrationComprehensive

class MasterTestRunner:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
        self.start_time = None
        self.end_time = None

    async def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Comprehensive API Test Suite")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        self.start_time = datetime.now()
        
        # Test suites to run
        test_suites = [
            ("Authentication", TestAuthEndpoints),
            ("Users", TestUsersEndpoints),
            ("Files", TestFilesEndpoints),
            ("Documents", TestDocumentsEndpoints),
            ("Calculations", TestCalculationsEndpoints),
            ("Orders", TestOrdersEndpoints),
            ("Call Requests", TestCallRequestsEndpoints),
            ("Bitrix", TestBitrixEndpoints),
            ("Integration", TestIntegrationComprehensive)
        ]
        
        # Run each test suite
        for suite_name, test_class in test_suites:
            print(f"\n{'='*20} {suite_name} Tests {'='*20}")
            try:
                tester = test_class(self.base_url)
                success = await tester.run_all_tests()
                self.results[suite_name] = success
                
                if success:
                    print(f"✅ {suite_name} tests PASSED")
                else:
                    print(f"❌ {suite_name} tests FAILED")
                    
            except Exception as e:
                print(f"❌ {suite_name} tests ERROR: {e}")
                self.results[suite_name] = False
        
        self.end_time = datetime.now()
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_suites = len(self.results)
        passed_suites = sum(1 for success in self.results.values() if success)
        failed_suites = total_suites - passed_suites
        
        print(f"Total Test Suites: {total_suites}")
        print(f"Passed: {passed_suites}")
        print(f"Failed: {failed_suites}")
        print(f"Success Rate: {(passed_suites/total_suites)*100:.1f}%")
        
        print(f"\nDuration: {self.end_time - self.start_time}")
        
        print("\nDetailed Results:")
        for suite_name, success in self.results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {suite_name}: {status}")
        
        if failed_suites > 0:
            print(f"\n❌ {failed_suites} test suite(s) failed!")
            return False
        else:
            print(f"\n🎉 All {total_suites} test suites passed!")
            return True

    async def run_specific_suite(self, suite_name: str):
        """Run a specific test suite"""
        suite_map = {
            "auth": TestAuthEndpoints,
            "users": TestUsersEndpoints,
            "files": TestFilesEndpoints,
            "documents": TestDocumentsEndpoints,
            "calculations": TestCalculationsEndpoints,
            "orders": TestOrdersEndpoints,
            "call-requests": TestCallRequestsEndpoints,
            "bitrix": TestBitrixEndpoints,
            "integration": TestIntegrationComprehensive
        }
        
        if suite_name not in suite_map:
            print(f"❌ Unknown test suite: {suite_name}")
            print(f"Available suites: {', '.join(suite_map.keys())}")
            return False
        
        print(f"🧪 Running {suite_name} test suite...")
        tester = suite_map[suite_name](self.base_url)
        return await tester.run_all_tests()


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run API tests")
    parser.add_argument("--suite", help="Run specific test suite", 
                       choices=["auth", "users", "files", "documents", "calculations", 
                               "orders", "call-requests", "bitrix", "integration"])
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="Base URL for API (default: http://localhost:8000)")
    
    args = parser.parse_args()
    
    runner = MasterTestRunner(args.url)
    
    if args.suite:
        success = await runner.run_specific_suite(args.suite)
        sys.exit(0 if success else 1)
    else:
        success = await runner.run_all_tests()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
