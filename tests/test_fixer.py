from pathlib import Path
from selftest.fixer.patch_generator import generate_patches, format_diff, PatchSuggestion
from selftest.fixer.interactive_apply import apply_patches, restore_backup
from selftest.fixer.roo_exporter import export_roo_instruction
from selftest.models import (
    TestResult, SingleTestResult, CoverageInfo, RuleViolation, AnalysisResult,
)


def _make_result(file_path="test.py"):
    return TestResult(
        file_path=file_path,
        generated_test_path=".selftest/tests/test__test.py",
        passed=2, failed=1, errors=0,
        details=[
            SingleTestResult(
                test_name="test_fail", path_description="mismatch",
                status="failed", cause="data too short", suggestion="add len check",
                line_range=(3, 3),
            ),
        ],
        coverage=CoverageInfo(3, 2, 66.7, [3], {}),
        rule_violations=[
            RuleViolation(
                rule_id="no_bare_except", description="bare except",
                severity="error", file_path=file_path, line=5,
                code_snippet="except:", suggestion="Use specific exception",
            )
        ],
        assertion_quality_ok=True,
        verification_rounds=1,
    )


# --- Patch Generator ---

def test_generate_patches(tmp_path):
    source = tmp_path / "test.py"
    source.write_text("line1\nline2\nline3\nline4\nexcept:\n", encoding="utf-8")
    result = _make_result(str(source))
    patches = generate_patches(result, source)
    assert len(patches) == 2  # 1 rule violation + 1 failed test


def test_format_diff():
    patch = PatchSuggestion(
        index=1, line=5, description="bare except",
        original="except:", replacement="except Exception:",
        file_path="test.py",
    )
    diff = format_diff(patch)
    assert "[1]" in diff
    assert "L5" in diff
    assert "- except:" in diff
    assert "+ except Exception:" in diff


def test_no_patches_for_clean_result(tmp_path):
    source = tmp_path / "test.py"
    source.write_text("clean code\n", encoding="utf-8")
    result = TestResult(
        file_path=str(source), generated_test_path="",
        passed=1, failed=0, errors=0, details=[],
        coverage=CoverageInfo(1, 1, 100.0, [], {}),
        rule_violations=[], assertion_quality_ok=True, verification_rounds=1,
    )
    patches = generate_patches(result, source)
    assert patches == []


# --- Interactive Apply ---

def test_apply_all_patches(tmp_path):
    source = tmp_path / "test.py"
    source.write_text("line1\nline2\nline3\n", encoding="utf-8")
    backup_dir = tmp_path / "backups"

    patches = [
        PatchSuggestion(1, 2, "fix line 2", "line2", "fixed_line2", str(source)),
    ]
    applied = apply_patches(patches, source, backup_dir)
    assert applied == [1]

    content = source.read_text(encoding="utf-8")
    assert "fixed_line2" in content
    assert (backup_dir / "test.py.bak").exists()


def test_apply_selected_patches(tmp_path):
    source = tmp_path / "test.py"
    source.write_text("line1\nline2\nline3\n", encoding="utf-8")
    backup_dir = tmp_path / "backups"

    patches = [
        PatchSuggestion(1, 1, "fix 1", "line1", "fixed1", str(source)),
        PatchSuggestion(2, 3, "fix 3", "line3", "fixed3", str(source)),
    ]
    applied = apply_patches(patches, source, backup_dir, selected_indices=[2])
    assert applied == [2]

    content = source.read_text(encoding="utf-8")
    assert "line1" in content  # not changed
    assert "fixed3" in content  # changed


def test_restore_backup(tmp_path):
    source = tmp_path / "test.py"
    source.write_text("original\n", encoding="utf-8")
    backup_dir = tmp_path / "backups"

    patches = [PatchSuggestion(1, 1, "fix", "original", "modified", str(source))]
    apply_patches(patches, source, backup_dir)
    assert "modified" in source.read_text(encoding="utf-8")

    restored = restore_backup(source, backup_dir)
    assert restored is True
    assert "original" in source.read_text(encoding="utf-8")


def test_restore_no_backup(tmp_path):
    source = tmp_path / "test.py"
    source.write_text("content\n", encoding="utf-8")
    result = restore_backup(source, tmp_path / "nonexistent")
    assert result is False


# --- Roo Exporter ---

def test_export_roo_instruction(tmp_path):
    result = _make_result()
    output = tmp_path / "roo" / "fix_test.md"
    target = tmp_path / "test.py"
    target.write_text("dummy", encoding="utf-8")

    path = export_roo_instruction(result, analysis=None, target_file=target, output_path=output)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "test_fail" in content
    assert "data too short" in content
    assert "add len check" in content
    assert "bare except" in content


def test_export_roo_with_analysis(tmp_path):
    result = _make_result()
    analysis = AnalysisResult(
        file_path="test.py", functions=[], imports=["tester"], mock_targets=["tester"],
    )
    output = tmp_path / "fix.md"
    target = tmp_path / "test.py"
    target.write_text("dummy", encoding="utf-8")

    export_roo_instruction(result, analysis, target, output)
    content = output.read_text(encoding="utf-8")
    assert "tester" in content  # mock target mentioned in constraints


def test_export_roo_no_failures(tmp_path):
    result = TestResult(
        file_path="test.py", generated_test_path="",
        passed=3, failed=0, errors=0, details=[],
        coverage=CoverageInfo(3, 3, 100.0, [], {}),
        rule_violations=[], assertion_quality_ok=True, verification_rounds=1,
    )
    output = tmp_path / "fix.md"
    target = tmp_path / "test.py"
    target.write_text("dummy", encoding="utf-8")

    export_roo_instruction(result, None, target, output)
    content = output.read_text(encoding="utf-8")
    assert "selftest" in content  # still generates the file
