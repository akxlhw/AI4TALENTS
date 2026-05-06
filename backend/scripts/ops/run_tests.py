#!/usr/bin/env python
"""
Test Runner for Academic Talent System
学术人才子系统测试运行脚本

Usage:
    python scripts/run_tests.py                    # Run all tests
    python scripts/run_tests.py --unit             # Run unit tests only
    python scripts/run_tests.py --integration      # Run integration tests
    python scripts/run_tests.py --e2e              # Run E2E tests
    python scripts/run_tests.py --collect          # Run collect tests
    python scripts/run_tests.py --cov              # Run with coverage
"""
import subprocess
import sys
import argparse


def run_tests(test_type: str = "all", coverage: bool = False, verbose: bool = True):
    """Run tests based on type."""

    # Base command
    cmd = ["pytest"]

    # Add verbose flag
    if verbose:
        cmd.append("-v")

    # Add coverage
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html:htmlcov"])

    # Select test type
    if test_type == "unit":
        cmd.extend(["-m", "unit", "tests/"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration", "tests/"])
    elif test_type == "e2e":
        cmd.extend(["-m", "e2e", "tests/"])
    elif test_type == "collect":
        # Collect specific tests
        cmd.extend(["tests/test_collect.py", "tests/services/test_collect_service.py", "tests/test_data_flow_e2e.py"])
    elif test_type == "fast":
        # Skip slow tests
        cmd.extend(["-m", "not slow", "tests/"])
    else:
        cmd.append("tests/")

    print(f"\n{'='*60}")
    print(f"Running tests: {test_type}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd)

    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Test runner for Academic Talent System")

    parser.add_argument(
        "--unit", action="store_true",
        help="Run unit tests only"
    )
    parser.add_argument(
        "--integration", action="store_true",
        help="Run integration tests only"
    )
    parser.add_argument(
        "--e2e", action="store_true",
        help="Run end-to-end tests only"
    )
    parser.add_argument(
        "--collect", action="store_true",
        help="Run collect configuration tests"
    )
    parser.add_argument(
        "--fast", action="store_true",
        help="Run fast tests (skip slow tests)"
    )
    parser.add_argument(
        "--cov", "--coverage", action="store_true",
        help="Run with coverage report"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="Reduce output verbosity"
    )

    args = parser.parse_args()

    # Determine test type
    if args.unit:
        test_type = "unit"
    elif args.integration:
        test_type = "integration"
    elif args.e2e:
        test_type = "e2e"
    elif args.collect:
        test_type = "collect"
    elif args.fast:
        test_type = "fast"
    else:
        test_type = "all"

    # Run tests
    exit_code = run_tests(
        test_type=test_type,
        coverage=args.cov,
        verbose=not args.quiet
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
