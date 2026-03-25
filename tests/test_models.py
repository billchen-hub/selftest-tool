from selftest.models import (
    FunctionCall, Branch, RandomVar, FunctionInfo, AnalysisResult,
    RuleViolation, SingleTestResult, CoverageInfo, TestResult,
)


def test_function_call_creation():
    fc = FunctionCall(module="tester", method="send_cmd", args=["GET_VERSION"], line=10)
    assert fc.module == "tester"
    assert fc.line == 10


def test_analysis_result_roundtrip():
    original = AnalysisResult(
        file_path="test.py",
        functions=[
            FunctionInfo(
                name="my_func",
                params=["device"],
                external_calls=[FunctionCall("tester", "send_cmd", ["READ"], 5)],
                branches=[Branch("resp.status != 0", 6, ["True", "False"])],
                total_paths=2,
                return_types=["bool"],
                random_variables=[
                    RandomVar(
                        name="addr", source="random.randint(0, 100)",
                        range_min=0, range_max=100,
                        boundary_values=[0, 50, 100],
                    )
                ],
            )
        ],
        imports=["tester", "log"],
        mock_targets=["tester"],
    )
    data = original.to_dict()
    loaded = AnalysisResult.from_dict(data)
    assert loaded.file_path == "test.py"
    assert loaded.imports == ["tester", "log"]
    assert loaded.functions[0].name == "my_func"
    assert loaded.functions[0].external_calls[0].module == "tester"
    assert loaded.functions[0].random_variables[0].range_max == 100


def test_test_result_roundtrip():
    original = TestResult(
        file_path="test.py",
        generated_test_path=".selftest/tests/test__test.py",
        passed=5, failed=1, errors=0,
        details=[
            SingleTestResult(
                test_name="test_fail", path_description="version mismatch",
                status="failed", expected="False", actual="IndexError",
                traceback="...", cause="data too short", suggestion="add len check",
                line_range=(52, 52),
            )
        ],
        coverage=CoverageInfo(
            total_paths=6, covered_paths=5, coverage_percent=83.3,
            uncovered_lines=[42], boundary_tests={"addr": True},
        ),
        rule_violations=[
            RuleViolation(
                rule_id="no_bare_except", description="No bare except",
                severity="error", file_path="test.py", line=10,
                code_snippet="except:", suggestion="Use specific exception",
            )
        ],
        assertion_quality_ok=True,
        verification_rounds=1,
    )
    data = original.to_dict()
    loaded = TestResult.from_dict(data)
    assert loaded.passed == 5
    assert loaded.failed == 1
    assert loaded.coverage.coverage_percent == 83.3
    assert loaded.details[0].line_range == (52, 52)
    assert loaded.rule_violations[0].rule_id == "no_bare_except"


def test_single_test_result_none_line_range():
    r = SingleTestResult(
        test_name="t", path_description="p", status="passed",
    )
    data = r.to_dict()
    assert data["line_range"] is None
    loaded = SingleTestResult.from_dict(data)
    assert loaded.line_range is None
