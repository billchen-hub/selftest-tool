"""Generate patch suggestions from test results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from selftest.models import TestResult


@dataclass
class PatchSuggestion:
    index: int
    line: int
    description: str
    original: str
    replacement: str
    file_path: str


def generate_patches(result: TestResult, source_file: Path) -> list[PatchSuggestion]:
    """Generate patch suggestions from failed tests and rule violations.

    Args:
        result: test execution result
        source_file: path to the original source file

    Returns:
        List of PatchSuggestion objects
    """
    if not source_file.exists():
        return []

    source_lines = source_file.read_text(encoding="utf-8").splitlines()
    patches = []
    idx = 1

    # Patches from rule violations
    for v in result.rule_violations:
        if v.line <= len(source_lines):
            original_line = source_lines[v.line - 1]
            patches.append(PatchSuggestion(
                index=idx,
                line=v.line,
                description=f"[{v.severity}] {v.description}",
                original=original_line,
                replacement=f"# TODO: {v.suggestion}\n{original_line}",
                file_path=str(source_file),
            ))
            idx += 1

    # Patches from failed tests with suggestions
    for detail in result.details:
        if detail.status == "failed" and detail.suggestion and detail.line_range:
            start_line = detail.line_range[0]
            if start_line <= len(source_lines):
                original_line = source_lines[start_line - 1]
                patches.append(PatchSuggestion(
                    index=idx,
                    line=start_line,
                    description=f"{detail.test_name}: {detail.cause or 'test failed'}",
                    original=original_line,
                    replacement=f"# FIXME: {detail.suggestion}\n{original_line}",
                    file_path=str(source_file),
                ))
                idx += 1

    return patches


def format_diff(patch: PatchSuggestion) -> str:
    """Format a patch as a readable diff."""
    lines = []
    lines.append(f"  [{patch.index}] L{patch.line}: {patch.description}")
    lines.append(f"      - {patch.original.strip()}")
    for repl_line in patch.replacement.splitlines():
        lines.append(f"      + {repl_line.strip()}")
    return "\n".join(lines)
