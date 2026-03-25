"""Run pytest on generated test files and collect results."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from selftest.models import SingleTestResult, CoverageInfo, TestResult


def run_tests(
    test_file: Path,
    source_file: Path | None = None,
    selftest_dir: Path | None = None,
) -> TestResult:
    """Run pytest on a test file and return structured results.

    Args:
        test_file: path to the generated pytest file
        source_file: path to the original source file (for coverage)
        selftest_dir: .selftest directory for storing intermediate data
    """
    test_file = Path(test_file)
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_file),
        "-v",
        "--tb=short",
    ]

    # Add coverage if source file provided
    if source_file is not None:
        cmd.extend([
            f"--cov={source_file.parent}",
            f"--cov-report=json:{selftest_dir or '.'}/coverage.json",
        ])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )

    test_result = _parse_pytest_output(
        result.stdout, result.stderr, result.returncode,
        test_file=str(test_file),
        source_file=str(source_file) if source_file else "",
    )

    # Override with real coverage data if available
    if source_file is not None and selftest_dir is not None:
        from selftest.runner.coverage import parse_coverage_json
        cov_json = Path(selftest_dir) / "coverage.json"
        real_cov = parse_coverage_json(cov_json, str(source_file))
        if real_cov is not None:
            test_result.coverage = real_cov

    return test_result


def _parse_pytest_output(
    stdout: str, stderr: str, returncode: int,
    test_file: str, source_file: str,
) -> TestResult:
    """Parse pytest verbose output into TestResult."""
    details = []
    passed = 0
    failed = 0
    errors = 0

    for line in stdout.splitlines():
        line = line.strip()
        if " PASSED" in line:
            test_name = line.split(" PASSED")[0].strip()
            # Extract just the test function name
            if "::" in test_name:
                test_name = test_name.split("::")[-1]
            details.append(SingleTestResult(
                test_name=test_name,
                path_description="",
                status="passed",
            ))
            passed += 1
        elif " FAILED" in line:
            test_name = line.split(" FAILED")[0].strip()
            if "::" in test_name:
                test_name = test_name.split("::")[-1]
            details.append(SingleTestResult(
                test_name=test_name,
                path_description="",
                status="failed",
            ))
            failed += 1
        elif " ERROR" in line:
            test_name = line.split(" ERROR")[0].strip()
            if "::" in test_name:
                test_name = test_name.split("::")[-1]
            details.append(SingleTestResult(
                test_name=test_name,
                path_description="",
                status="error",
            ))
            errors += 1

    # Extract failure details from stderr or stdout
    _enrich_failure_details(stdout + "\n" + stderr, details)

    coverage = CoverageInfo(
        total_paths=passed + failed + errors,
        covered_paths=passed,
        coverage_percent=round(passed / max(passed + failed + errors, 1) * 100, 1),
        uncovered_lines=[],
        boundary_tests={},
    )

    return TestResult(
        file_path=source_file,
        generated_test_path=test_file,
        passed=passed,
        failed=failed,
        errors=errors,
        details=details,
        coverage=coverage,
        rule_violations=[],
        assertion_quality_ok=True,
        verification_rounds=1,
    )


def _enrich_failure_details(output: str, details: list[SingleTestResult]) -> None:
    """Extract traceback info and enrich failed test details."""
    # Simple heuristic: look for FAILED lines followed by assertion info
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if "AssertionError" in line or "assert" in line.lower():
            # Find which test this belongs to
            for detail in details:
                if detail.status == "failed" and detail.actual is None:
                    detail.actual = line.strip()
                    # Look for context in surrounding lines
                    context = lines[max(0, i - 3):i + 1]
                    detail.traceback = "\n".join(context)
                    break
