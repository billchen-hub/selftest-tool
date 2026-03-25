from selftest.analyzer.random_detector import detect_random_vars


def test_detect_randint(fixtures_dir):
    source = (fixtures_dir / "random_script.py").read_text()
    randoms = detect_random_vars(source)
    addr_var = [r for r in randoms if r.name == "addr"][0]
    assert addr_var.range_min == 0x0000
    assert addr_var.range_max == 0xFFFF
    assert any("addr > 0xFFF0" in b or "addr > 65520" in b for b in addr_var.affects_branches)
    assert 0x0000 in addr_var.boundary_values
    assert 0xFFFF in addr_var.boundary_values
    assert 0xFFF0 in addr_var.boundary_values
    assert 0xFFF1 in addr_var.boundary_values


def test_detect_random_choice(fixtures_dir):
    source = (fixtures_dir / "random_script.py").read_text()
    randoms = detect_random_vars(source)
    size_var = [r for r in randoms if r.name == "size"][0]
    assert size_var.enum_values == [512, 1024, 4096]
    assert size_var.boundary_values == [512, 1024, 4096]


def test_no_random_vars(fixtures_dir):
    source = (fixtures_dir / "simple_script.py").read_text()
    randoms = detect_random_vars(source)
    assert randoms == []


def test_midpoint_included():
    source = """
import random
def foo():
    x = random.randint(0, 100)
    if x > 50:
        return True
    return False
"""
    randoms = detect_random_vars(source)
    assert len(randoms) == 1
    assert 50 in randoms[0].boundary_values  # midpoint = 50
    assert 0 in randoms[0].boundary_values
    assert 100 in randoms[0].boundary_values
    assert 49 in randoms[0].boundary_values  # threshold - 1
    assert 51 in randoms[0].boundary_values  # threshold + 1
