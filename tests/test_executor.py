from pathlib import Path
from selftest.runner.executor import run_tests


def test_run_passing_tests(tmp_path):
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("""
def test_pass():
    assert 1 + 1 == 2

def test_also_pass():
    assert "hello" == "hello"
""")
    result = run_tests(test_file, source_file=None, selftest_dir=tmp_path)
    assert result.passed == 2
    assert result.failed == 0
    assert result.errors == 0


def test_run_failing_tests(tmp_path):
    test_file = tmp_path / "test_fail.py"
    test_file.write_text("""
def test_fail():
    assert 1 == 2
""")
    result = run_tests(test_file, source_file=None, selftest_dir=tmp_path)
    assert result.failed == 1
    assert result.passed == 0


def test_run_mixed_results(tmp_path):
    test_file = tmp_path / "test_mixed.py"
    test_file.write_text("""
def test_pass():
    assert True == True

def test_fail():
    assert 1 == 99
""")
    result = run_tests(test_file, source_file=None, selftest_dir=tmp_path)
    assert result.passed == 1
    assert result.failed == 1


def test_result_serialization(tmp_path):
    test_file = tmp_path / "test_s.py"
    test_file.write_text("def test_ok(): assert 1 == 1\n")
    result = run_tests(test_file, source_file=None, selftest_dir=tmp_path)
    data = result.to_dict()
    from selftest.models import TestResult
    loaded = TestResult.from_dict(data)
    assert loaded.passed == result.passed
