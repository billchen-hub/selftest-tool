from pathlib import Path
from selftest.rules.engine import load_rules, check_rules, Rule


def test_load_builtin_rules():
    rules = load_rules()
    assert len(rules) > 0
    ids = [r.id for r in rules]
    assert "no_bare_except" in ids
    assert "no_assert_true" in ids


def test_load_project_override(tmp_path):
    project_default = tmp_path / "default.yaml"
    project_default.write_text("""
rules:
  - id: no_bare_except
    description: "overridden description"
    severity: disabled
    match:
      pattern: "except\\\\s*:"
""", encoding="utf-8")
    rules = load_rules(project_default_path=project_default)
    # no_bare_except should be disabled (filtered out)
    ids = [r.id for r in rules]
    assert "no_bare_except" not in ids


def test_load_custom_rules(tmp_path):
    custom = tmp_path / "custom.yaml"
    custom.write_text("""
rules:
  - id: custom_check
    description: "custom rule"
    severity: error
    match:
      pattern: "TODO"
""", encoding="utf-8")
    rules = load_rules(project_custom_path=custom)
    ids = [r.id for r in rules]
    assert "custom_check" in ids
    # builtin rules should still be there
    assert "no_bare_except" in ids


def test_check_bare_except():
    source = """
try:
    do_something()
except:
    pass
"""
    rules = load_rules()
    violations = check_rules(source, "test.py", rules)
    ids = [v.rule_id for v in violations]
    assert "no_bare_except" in ids


def test_check_assert_true():
    source = """
def test_foo():
    assert True
"""
    rules = load_rules()
    violations = check_rules(source, "test.py", rules)
    ids = [v.rule_id for v in violations]
    assert "no_assert_true" in ids


def test_check_clean_code():
    source = """
def add(a, b):
    return a + b
"""
    rules = load_rules()
    violations = check_rules(source, "test.py", rules)
    assert len(violations) == 0


def test_check_exit_call():
    source = """
import sys
sys.exit(1)
"""
    rules = load_rules()
    violations = check_rules(source, "test.py", rules)
    ids = [v.rule_id for v in violations]
    assert "no_exit_call" in ids


def test_violation_has_line_number():
    source = "line1\nline2\nexcept:\nline4"
    rules = [Rule(id="test", description="test", severity="error", pattern="except\\s*:")]
    violations = check_rules(source, "test.py", rules)
    assert len(violations) == 1
    assert violations[0].line == 3


def test_load_invalid_yaml(tmp_path):
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("{{invalid yaml", encoding="utf-8")
    rules = load_rules(project_custom_path=bad_file)
    # Should not crash, just use builtin rules
    assert len(rules) > 0


def test_load_nonexistent_file():
    rules = load_rules(project_custom_path=Path("nonexistent.yaml"))
    # Should not crash
    assert len(rules) > 0
