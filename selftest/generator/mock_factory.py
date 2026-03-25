"""Generate mock setup code for test files."""

from __future__ import annotations

from selftest.models import AnalysisResult


def generate_mock_setup(
    analysis: AnalysisResult,
    mock_returns: dict | None = None,
) -> str:
    """Generate mock import and setup code for pytest test file.

    Args:
        analysis: AST analysis result
        mock_returns: dict of "module.method" → {"default": {...}, "error_case": {...}}

    Returns:
        Python code string with mock setup
    """
    if mock_returns is None:
        mock_returns = {}

    lines = [
        "import pytest",
        "from unittest.mock import MagicMock, patch",
        "",
    ]

    # Generate mock fixtures/helpers for each mock target
    for target in analysis.mock_targets:
        # Collect all methods called on this target
        methods = set()
        for func in analysis.functions:
            for call in func.external_calls:
                if call.module == target:
                    methods.add(call.method)

        lines.append(f"# Mock setup for '{target}'")
        lines.append(f"def create_{target}_mock():")
        lines.append(f"    mock = MagicMock()")

        for method in sorted(methods):
            key = f"{target}.{method}"
            if key in mock_returns and "default" in mock_returns[key]:
                default_val = mock_returns[key]["default"]
                lines.append(f"    mock.{method}.return_value = MagicMock(**{default_val!r})")
            else:
                lines.append(f"    mock.{method}.return_value = MagicMock(status=0, data='mock_data')")

        lines.append(f"    return mock")
        lines.append("")

    return "\n".join(lines)
