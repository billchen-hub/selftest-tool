"""Tests for dry-run test generator."""

from selftest.generator.dry_run import generate_dry_run_tests
from selftest.models import (
    AnalysisResult, FunctionInfo, FunctionCall, Branch, RandomVar,
)


def _make_analysis(functions=None, imports=None, mock_targets=None):
    return AnalysisResult(
        file_path="test_script.py",
        functions=functions or [],
        imports=imports or [],
        mock_targets=mock_targets or [],
    )


def _make_func(name="my_func", params=None, branches=None,
               external_calls=None, random_variables=None, total_paths=1):
    return FunctionInfo(
        name=name,
        params=params or ["a", "b"],
        branches=branches or [],
        external_calls=external_calls or [],
        return_types=["bool"],
        random_variables=random_variables or [],
        total_paths=total_paths,
    )


class TestGenerateDryRunTests:
    def test_generates_valid_python(self):
        func = _make_func()
        analysis = _make_analysis(functions=[func])
        code = generate_dry_run_tests(analysis)
        compile(code, "<dry_run>", "exec")  # no SyntaxError

    def test_includes_class_per_function(self):
        f1 = _make_func(name="func_a")
        f2 = _make_func(name="func_b")
        analysis = _make_analysis(functions=[f1, f2])
        code = generate_dry_run_tests(analysis)
        assert "class TestDryRun_func_a:" in code
        assert "class TestDryRun_func_b:" in code

    def test_includes_happy_path_test(self):
        func = _make_func(name="check_fw")
        analysis = _make_analysis(functions=[func])
        code = generate_dry_run_tests(analysis)
        assert "def test_check_fw_happy_path(self):" in code

    def test_includes_analysis_structure_test(self):
        func = _make_func(name="verify", total_paths=6,
                          branches=[Branch("x > 0", 5, ["true", "false"])])
        analysis = _make_analysis(functions=[func])
        code = generate_dry_run_tests(analysis)
        assert "def test_verify_analysis_structure(self):" in code
        assert "assert 6 >= 1" in code

    def test_includes_boundary_values(self):
        rv = RandomVar(name="addr", source="random.randint(0, 0xFFFF)",
                       range_min=0, range_max=65535,
                       boundary_values=[0, 65535, 100, 99, 101])
        func = _make_func(name="rw_test", random_variables=[rv])
        analysis = _make_analysis(functions=[func])
        code = generate_dry_run_tests(analysis)
        assert "boundary values" in code.lower()
        assert "[0, 65535, 100, 99, 101]" in code

    def test_mocks_external_calls(self):
        call = FunctionCall(module="tester", method="send_cmd",
                            args=["cmd", "dev"], line=10)
        func = _make_func(name="run_cmd", external_calls=[call])
        analysis = _make_analysis(functions=[func],
                                  imports=["tester"],
                                  mock_targets=["tester"])
        code = generate_dry_run_tests(analysis)
        assert "send_cmd" in code
        assert "tester" in code

    def test_empty_functions(self):
        analysis = _make_analysis(functions=[])
        code = generate_dry_run_tests(analysis)
        compile(code, "<dry_run_empty>", "exec")
        assert "class TestDryRun" not in code

    def test_can_be_called_test(self):
        func = _make_func(name="init_device")
        analysis = _make_analysis(functions=[func])
        code = generate_dry_run_tests(analysis)
        assert "def test_init_device_can_be_called(self):" in code
        assert "hasattr(mod, 'init_device')" in code
