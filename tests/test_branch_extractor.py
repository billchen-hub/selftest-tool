from selftest.analyzer.branch_extractor import extract_branches


def test_extract_simple_if_else(fixtures_dir):
    source = (fixtures_dir / "simple_script.py").read_text()
    functions = extract_branches(source)
    names = [f.name for f in functions]
    assert "add" in names
    assert "greet" in names

    greet = [f for f in functions if f.name == "greet"][0]
    assert len(greet.branches) == 1
    assert greet.total_paths == 2


def test_extract_if_elif_else(fixtures_dir):
    source = (fixtures_dir / "branching_script.py").read_text()
    functions = extract_branches(source)
    verify = [f for f in functions if f.name == "verify_firmware_version"][0]
    # 3 top-level branch points: status check, device type (if/elif/else), version match
    assert len(verify.branches) == 3
    # status: 2, device: 3, version: 2 → 2*3*2 = 12
    # but device type's if/elif/else has 3 paths, total = 2*3*2 = 12
    assert verify.total_paths == 12


def test_extract_nested_branches(fixtures_dir):
    source = (fixtures_dir / "random_script.py").read_text()
    functions = extract_branches(source)
    write = [f for f in functions if f.name == "write_random_blocks"][0]
    # outer if (status), inner if (addr) → 2 branch points
    assert len(write.branches) == 2


def test_extract_external_calls(fixtures_dir):
    source = (fixtures_dir / "branching_script.py").read_text()
    functions = extract_branches(source)
    verify = [f for f in functions if f.name == "verify_firmware_version"][0]
    call_strs = [f"{c.module}.{c.method}" for c in verify.external_calls]
    assert "tester.send_cmd" in call_strs
    assert "log.error" in call_strs
    assert "log.warning" in call_strs


def test_extract_return_types(fixtures_dir):
    source = (fixtures_dir / "branching_script.py").read_text()
    functions = extract_branches(source)
    verify = [f for f in functions if f.name == "verify_firmware_version"][0]
    assert "bool" in verify.return_types
    assert "raises ValueError" in verify.return_types


def test_multi_function(fixtures_dir):
    source = (fixtures_dir / "multi_function_script.py").read_text()
    functions = extract_branches(source)
    assert len(functions) == 2
    names = {f.name for f in functions}
    assert names == {"init_device", "read_register"}


def test_no_branches():
    source = "def foo():\n    return 42\n"
    functions = extract_branches(source)
    assert len(functions) == 1
    assert functions[0].branches == []
    assert functions[0].total_paths == 1
