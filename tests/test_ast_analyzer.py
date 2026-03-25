from selftest.analyzer.ast_analyzer import analyze_file
from selftest.models import AnalysisResult


def test_analyze_branching_script(fixtures_dir):
    result = analyze_file(
        fixtures_dir / "branching_script.py",
        mock_modules=["tester"], never_mock=[],
    )
    assert isinstance(result, AnalysisResult)
    assert len(result.functions) == 1
    assert result.functions[0].name == "verify_firmware_version"
    assert len(result.functions[0].external_calls) > 0
    assert "tester" in result.mock_targets


def test_analyze_random_script(fixtures_dir):
    result = analyze_file(
        fixtures_dir / "random_script.py",
        mock_modules=["tester"], never_mock=[],
    )
    func = result.functions[0]
    assert len(func.random_variables) == 2
    assert func.total_paths >= 2


def test_analyze_multi_function(fixtures_dir):
    result = analyze_file(
        fixtures_dir / "multi_function_script.py",
        mock_modules=["tester"], never_mock=[],
    )
    assert len(result.functions) == 2
    names = {f.name for f in result.functions}
    assert names == {"init_device", "read_register"}


def test_analyze_simple_script(fixtures_dir):
    result = analyze_file(
        fixtures_dir / "simple_script.py",
        mock_modules=[], never_mock=[],
    )
    assert len(result.functions) == 2
    assert result.mock_targets == []
    # simple_script has no random vars
    for f in result.functions:
        assert f.random_variables == []
