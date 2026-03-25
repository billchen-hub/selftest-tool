from io import StringIO
from selftest.reporter.terminal import render_terminal_report
from selftest.models import (
    TestResult, SingleTestResult, CoverageInfo, RuleViolation, AnalysisResult,
    FunctionInfo, Branch, FunctionCall,
)


def test_render_report_contains_key_info():
    result = TestResult(
        file_path="test_case_001.py",
        generated_test_path=".selftest/tests/test__test_case_001.py",
        passed=5, failed=1, errors=0,
        details=[SingleTestResult(
            test_name="test_fail", path_description="version mismatch",
            status="failed", expected="False", actual="IndexError",
            traceback="...", cause="data too short", suggestion="add len check",
            line_range=(52, 52),
        )],
        coverage=CoverageInfo(
            total_paths=6, covered_paths=5, coverage_percent=83.3,
            uncovered_lines=[89], boundary_tests={"addr": True},
        ),
        rule_violations=[],
        assertion_quality_ok=True,
        verification_rounds=1,
    )
    output = StringIO()
    render_terminal_report(result, file=output)
    text = output.getvalue()
    assert "5 passed" in text
    assert "1 failed" in text
    assert "83.3" in text


def test_render_with_analysis():
    analysis = AnalysisResult(
        file_path="test.py",
        functions=[FunctionInfo(
            name="foo", params=["x"],
            external_calls=[FunctionCall("tester", "cmd", [], 1)],
            branches=[Branch("x > 0", 2, ["True", "False"])],
            total_paths=2, return_types=["int"],
        )],
        imports=["tester"], mock_targets=["tester"],
    )
    result = TestResult(
        file_path="test.py", generated_test_path="t.py",
        passed=2, failed=0, errors=0, details=[],
        coverage=CoverageInfo(2, 2, 100.0, [], {}),
        rule_violations=[], assertion_quality_ok=True, verification_rounds=1,
    )
    output = StringIO()
    render_terminal_report(result, analysis=analysis, file=output)
    text = output.getvalue()
    assert "1" in text  # 1 function
    assert "2 passed" in text


def test_render_with_violations():
    result = TestResult(
        file_path="test.py", generated_test_path="t.py",
        passed=3, failed=0, errors=0, details=[],
        coverage=CoverageInfo(3, 3, 100.0, [], {}),
        rule_violations=[RuleViolation(
            rule_id="test", description="bare except", severity="error",
            file_path="test.py", line=10, code_snippet="except:", suggestion="fix",
        )],
        assertion_quality_ok=True, verification_rounds=1,
    )
    output = StringIO()
    render_terminal_report(result, file=output)
    text = output.getvalue()
    assert "bare except" in text
