"""
Test runner script for the trading pipeline.
Executes all tests and provides a summary report.
"""
import sys
import subprocess
import os
from pathlib import Path

# Add the backend directory to the path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def run_unit_tests():
    """Run unit tests"""
    print("\n" + "="*80)
    print("RUNNING UNIT TESTS")
    print("="*80)

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit/", "-v", "--tb=short"],
        cwd=BACKEND_DIR,
        capture_output=False
    )

    return result.returncode == 0


def run_integration_tests():
    """Run integration tests"""
    print("\n" + "="*80)
    print("RUNNING INTEGRATION TESTS")
    print("="*80)

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/integration/", "-v", "--tb=short"],
        cwd=BACKEND_DIR,
        capture_output=False
    )

    return result.returncode == 0


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("RUNNING ALL TESTS")
    print("="*80)

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=BACKEND_DIR,
        capture_output=False
    )

    return result.returncode == 0


def print_summary(unit_success, integration_success):
    """Print test summary"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    unit_status = "✅ PASSED" if unit_success else "❌ FAILED"
    integration_status = "✅ PASSED" if integration_success else "❌ FAILED"

    print(f"Unit Tests:        {unit_status}")
    print(f"Integration Tests: {integration_status}")

    if unit_success and integration_success:
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


def main():
    """Main test runner"""
    print("\n" + "="*80)
    print("CRYPTOTRADE BACKEND - TEST SUITE")
    print("="*80)
    print(f"Test directory: {BACKEND_DIR}/tests")
    print(f"Python version: {sys.version}")

    # Run tests
    unit_success = run_unit_tests()
    integration_success = run_integration_tests()

    # Print summary
    exit_code = print_summary(unit_success, integration_success)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
