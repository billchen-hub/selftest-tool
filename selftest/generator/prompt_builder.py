"""Assemble prompt from AST analysis results and user rules."""

from __future__ import annotations

from pathlib import Path
from selftest.models import AnalysisResult


_BASE_TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "_base.md"


def _load_base_template() -> str:
    if _BASE_TEMPLATE_PATH.exists():
        return _BASE_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _default_base_template()


def _default_base_template() -> str:
    return """You are a test generation assistant. Generate pytest test code for the given Python functions.

Requirements:
- Generate one test per execution path
- Use unittest.mock.patch to mock external dependencies
- Every test MUST have specific assertions (assert result == expected_value)
- Do NOT use weak assertions like: assert True, assert x is not None, assert isinstance
- For exception paths, use pytest.raises with match parameter
- Verify mock calls with assert_called_with or assert_called_once_with
- Include boundary value tests for random variables
- Add a docstring to each test describing which path it covers

Output format: Return ONLY valid Python code in a ```python code block.
"""


def _format_analysis(analysis: AnalysisResult) -> str:
    """Convert AnalysisResult to structured text for the prompt."""
    lines = [f"File: {analysis.file_path}"]
    lines.append(f"Modules to mock: {', '.join(analysis.mock_targets)}")
    lines.append("")

    for func in analysis.functions:
        lines.append(f"## Function: {func.name}({', '.join(func.params)})")
        lines.append(f"Return types: {', '.join(func.return_types)}")
        lines.append(f"Total paths: {func.total_paths}")

        if func.external_calls:
            lines.append("\nExternal calls:")
            for call in func.external_calls:
                lines.append(f"  - {call.module}.{call.method}({', '.join(call.args)}) at line {call.line}")

        if func.branches:
            lines.append("\nBranches:")
            for branch in func.branches:
                lines.append(f"  - Condition: {branch.condition} (line {branch.line})")
                for path in branch.paths:
                    lines.append(f"    - {path}")

        if func.random_variables:
            lines.append("\nRandom variables:")
            for rv in func.random_variables:
                lines.append(f"  - {rv.name} = {rv.source}")
                if rv.range_min is not None:
                    lines.append(f"    Range: [{rv.range_min}, {rv.range_max}]")
                if rv.enum_values:
                    lines.append(f"    Values: {rv.enum_values}")
                if rv.affects_branches:
                    lines.append(f"    Affects: {', '.join(rv.affects_branches)}")
                if rv.boundary_values:
                    lines.append(f"    Boundary test values: {rv.boundary_values}")

        lines.append("")

    return "\n".join(lines)


def _load_user_prompts(user_prompts_dir: Path | None) -> str:
    """Load all .md files from user prompts directory, sorted alphabetically."""
    if user_prompts_dir is None or not user_prompts_dir.exists():
        return ""

    parts = []
    for md_file in sorted(user_prompts_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8").strip()
        if content:
            parts.append(f"# Rules from {md_file.name}\n{content}")

    return "\n\n".join(parts)


def build_prompt(
    analysis: AnalysisResult,
    user_prompts_dir: Path | None = None,
) -> str:
    """Build complete prompt for AI test generation.

    Args:
        analysis: AST analysis result
        user_prompts_dir: path to .selftest/rules/prompts/

    Returns:
        Complete prompt string
    """
    parts = [
        _load_base_template(),
        _load_user_prompts(user_prompts_dir),
        "# Code Analysis\n",
        _format_analysis(analysis),
        "Generate the complete pytest test file now.",
    ]

    return "\n\n".join(p for p in parts if p.strip())
