"""
Enhanced pytest test runner with categorization and service detection
Runs tests using pytest with proper filtering and reporting
"""
import subprocess
import sys
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_pytest_command(args_list, description):
    """Run pytest with given arguments"""
    print(f"\n{'='*70}")
    print(f"{description}")
    print(f"{'='*70}")
    
    cmd = ["pytest"] + args_list
    print(f"Running: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced test runner for MaaS Backend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_pytest_tests.py --mode unit
    Run all fast unit tests with mocked dependencies

  python scripts/run_pytest_tests.py --mode integration  
    Run integration tests with real services

  python scripts/run_pytest_tests.py --mode all
    Run all tests (unit + integration + e2e)

  python scripts/run_pytest_tests.py --category security
    Run only security validation tests

  python scripts/run_pytest_tests.py --file tests/test_security_validation.py
    Run tests from specific file
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["unit", "integration", "e2e", "all"],
        default="unit",
        help="Test mode: unit (fast, mocked), integration (real services), e2e (complete), or all"
    )
    
    parser.add_argument(
        "--category",
        choices=["security", "validation", "error", "workflow", "performance", "service"],
        help="Run specific test category"
    )
    
    parser.add_argument(
        "--file",
        help="Run tests from specific file"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage reporting"
    )
    
    parser.add_argument(
        "--failfast",
        "-x",
        action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "--parallel",
        "-n",
        type=int,
        help="Run tests in parallel (requires pytest-xdist)"
    )
    
    args = parser.parse_args()
    
    # Build pytest arguments
    pytest_args = []
    
    # Add test directory
    if args.file:
        pytest_args.append(args.file)
    else:
        pytest_args.append("tests/")
    
    # Add markers based on mode
    if args.mode == "unit":
        pytest_args.extend(["-m", "unit"])
        description = "Running UNIT TESTS (fast, mocked dependencies)"
    elif args.mode == "integration":
        pytest_args.extend(["-m", "integration"])
        description = "Running INTEGRATION TESTS (real services required)"
    elif args.mode == "e2e":
        pytest_args.extend(["-m", "e2e"])
        description = "Running END-TO-END TESTS (complete system)"
    else:  # all
        description = "Running ALL TESTS (unit + integration + e2e)"
    
    # Add category marker if specified
    if args.category:
        category_map = {
            "security": "security",
            "validation": "unit",
            "error": "unit",
            "workflow": "e2e",
            "performance": "performance",
            "service": "integration",
        }
        
        if args.category in ["security", "performance"]:
            pytest_args.extend(["-m", args.category])
        
        # Add file filter for categories
        category_files = {
            "security": "tests/test_security_validation.py",
            "validation": "tests/test_data_validation.py",
            "error": "tests/test_error_handling.py",
            "workflow": "tests/test_workflows_*.py",
            "service": "tests/test_service_integration.py",
        }
        
        if args.category in category_files and not args.file:
            pytest_args.append(category_files[args.category])
        
        description = f"Running {args.category.upper()} TESTS"
    
    # Add verbosity
    if args.verbose:
        pytest_args.append("-v")
    else:
        pytest_args.append("-v")  # Always verbose for better output
    
    # Add coverage
    if args.coverage:
        pytest_args.extend([
            "--cov=backend",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    # Add fail-fast
    if args.failfast:
        pytest_args.append("-x")
    
    # Add parallel execution
    if args.parallel:
        pytest_args.extend(["-n", str(args.parallel)])
    
    # Add additional useful flags
    pytest_args.extend([
        "--tb=short",  # Short traceback format
        "--strict-markers",  # Enforce marker registration
    ])
    
    # Run tests
    success = run_pytest_command(pytest_args, description)
    
    if not success:
        print(f"\n{'='*70}")
        print("TESTS FAILED")
        print(f"{'='*70}")
        sys.exit(1)
    else:
        print(f"\n{'='*70}")
        print("ALL TESTS PASSED")
        print(f"{'='*70}")
        sys.exit(0)


if __name__ == "__main__":
    main()

