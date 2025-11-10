#!/usr/bin/env python3
"""
Comprehensive Test Runner

Runs all tests and generates detailed reports in tests/output/
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime


def run_unit_tests():
    """Run unit tests."""
    print("\n" + "="*70)
    print("RUNNING UNIT TESTS")
    print("="*70 + "\n")

    result = subprocess.run(
        ["python", "-m", "pytest", "tests/test_apis/", "tests/test_matching/", "-v"],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return result.returncode == 0


def run_integration_tests():
    """Run integration tests."""
    print("\n" + "="*70)
    print("RUNNING INTEGRATION TESTS")
    print("="*70 + "\n")

    result = subprocess.run(
        ["python", "tests/integration/test_complex_scenarios.py"],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return result.returncode == 0


def generate_report():
    """Generate comprehensive test report."""
    output_dir = Path("tests/output")

    # Find all test result files
    result_files = list(output_dir.glob("*.json"))

    report = {
        "generated": datetime.now().isoformat(),
        "total_result_files": len(result_files),
        "result_files": [str(f.name) for f in result_files],
        "summary": {}
    }

    # Check for test summary
    summary_files = list(output_dir.glob("test_summary_*.json"))
    if summary_files:
        latest_summary = sorted(summary_files)[-1]
        with open(latest_summary, 'r') as f:
            report["latest_test_summary"] = json.load(f)

    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"comprehensive_report_{timestamp}.json"

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n{'='*70}")
    print(f"Comprehensive report saved to: {report_file}")
    print(f"{'='*70}\n")

    return report


def main():
    """Main test runner."""
    print("\n" + "#"*70)
    print("#" + " " * 68 + "#")
    print("#" + " " * 20 + "TEST SUITE RUNNER" + " " * 31 + "#")
    print("#" + " " * 68 + "#")
    print("#"*70)

    # Run all tests
    unit_success = run_unit_tests()
    integration_success = run_integration_tests()

    # Generate report
    report = generate_report()

    # Summary
    print("\n" + "="*70)
    print("TEST SUITE SUMMARY")
    print("="*70)
    print(f"\nUnit Tests: {'✓ PASSED' if unit_success else '✗ FAILED'}")
    print(f"Integration Tests: {'✓ PASSED' if integration_success else '✗ FAILED'}")

    if 'latest_test_summary' in report:
        summary = report['latest_test_summary']
        print(f"\nTotal Tests Run: {summary.get('total_tests', 'N/A')}")
        print(f"Successes: {summary.get('successes', 'N/A')}")
        print(f"Failures: {summary.get('failures', 'N/A')}")
        print(f"Errors: {summary.get('errors', 'N/A')}")
        print(f"Success Rate: {summary.get('success_rate', 'N/A')}")

    print(f"\nTest outputs saved to: tests/output/")
    print("="*70 + "\n")

    # Exit with appropriate code
    sys.exit(0 if (unit_success and integration_success) else 1)


if __name__ == "__main__":
    main()
