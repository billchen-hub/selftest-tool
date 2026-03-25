from pathlib import Path
from selftest.reporter.html import generate_html_report
from selftest.models import (
    TestResult, SingleTestResult, CoverageInfo, RuleViolation,
)


def _make_result(**overrides) -> TestResult:
    defaults = dict(
        file_path="test_case_001.py",
        generated_test_path=".selftest/tests/test__test_case_001.py",
        passed=3, failed=1, errors=0,
        details=[
            SingleTestResult(test_name="test_ok", path_description="", status="passed"),
            SingleTestResult(test_name="test_ok2", path_description="", status="passed"),
            SingleTestResult(test_name="test_ok3", path_description="", status="passed"),
            SingleTestResult(
                test_name="test_fail", path_description="version mismatch",
                status="failed", cause="data too short", suggestion="add len check",
                actual="IndexError",
            ),
        ],
        coverage=CoverageInfo(
            total_paths=4, covered_paths=3, coverage_percent=75.0,
            uncovered_lines=[10, 11], boundary_tests={"addr": True},
        ),
        rule_violations=[
            RuleViolation(
                rule_id="no_bare_except", description="bare except",
                severity="error", file_path="test.py", line=5,
                code_snippet="except:", suggestion="use specific exception",
            )
        ],
        assertion_quality_ok=True,
        verification_rounds=1,
    )
    defaults.update(overrides)
    return TestResult(**defaults)


def test_generate_html_report(tmp_path):
    result = _make_result()
    output = tmp_path / "report.html"
    path = generate_html_report(result, output)
    assert path.exists()
    html = path.read_text(encoding="utf-8")
    assert "selftest report" in html
    assert "test_fail" in html
    assert "75.0%" in html
    assert "bare except" in html


def test_html_contains_all_tests(tmp_path):
    result = _make_result()
    output = tmp_path / "report.html"
    generate_html_report(result, output)
    html = output.read_text(encoding="utf-8")
    assert "test_ok" in html
    assert "test_ok2" in html
    assert "test_ok3" in html
    assert "test_fail" in html


def test_html_with_source_coverage(tmp_path):
    source = tmp_path / "test_case.py"
    source.write_text("line1\nline2\nline3\n", encoding="utf-8")

    result = _make_result(coverage=CoverageInfo(
        total_paths=3, covered_paths=2, coverage_percent=66.7,
        uncovered_lines=[2], boundary_tests={},
    ))
    output = tmp_path / "report.html"
    generate_html_report(result, output, source_file=source)
    html = output.read_text(encoding="utf-8")
    assert "line-uncovered" in html
    assert "line-covered" in html


def test_html_no_failures(tmp_path):
    result = _make_result(
        failed=0,
        details=[
            SingleTestResult(test_name="t1", path_description="", status="passed"),
        ],
        rule_violations=[],
    )
    output = tmp_path / "report.html"
    generate_html_report(result, output)
    html = output.read_text(encoding="utf-8")
    # No failed test details should be shown
    assert "FAILED" not in html
    assert "test_fail" not in html


def test_html_boundary_tests(tmp_path):
    result = _make_result()
    output = tmp_path / "report.html"
    generate_html_report(result, output)
    html = output.read_text(encoding="utf-8")
    assert "addr" in html
    assert "Boundary" in html
