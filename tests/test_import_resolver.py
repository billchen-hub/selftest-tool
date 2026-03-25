from selftest.analyzer.import_resolver import resolve_imports


def test_classify_imports(fixtures_dir):
    source = (fixtures_dir / "branching_script.py").read_text()
    result = resolve_imports(source, mock_modules=["tester"], never_mock=["log"])
    assert "tester" in result.mock_targets
    assert "log" not in result.mock_targets
    assert "log" in result.real_imports


def test_stdlib_not_mocked(fixtures_dir):
    source = (fixtures_dir / "random_script.py").read_text()
    result = resolve_imports(source, mock_modules=["tester"], never_mock=[])
    assert "random" not in result.mock_targets
    assert "random" in result.real_imports
    assert "tester" in result.mock_targets


def test_all_imports_collected(fixtures_dir):
    source = (fixtures_dir / "branching_script.py").read_text()
    result = resolve_imports(source, mock_modules=[], never_mock=[])
    assert "tester" in result.all_imports
    assert "log" in result.all_imports


def test_never_mock_overrides(fixtures_dir):
    source = (fixtures_dir / "branching_script.py").read_text()
    result = resolve_imports(source, mock_modules=["tester", "log"], never_mock=["log"])
    assert "tester" in result.mock_targets
    assert "log" not in result.mock_targets
    assert "log" in result.real_imports
