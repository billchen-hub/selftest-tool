"""Rich terminal output for selftest results."""

from __future__ import annotations

import sys
from io import StringIO

from selftest.models import TestResult, AnalysisResult


def render_terminal_report(
    result: TestResult,
    analysis: AnalysisResult | None = None,
    file=None,
) -> None:
    """Render test results to terminal using rich formatting.

    Args:
        result: test execution result
        analysis: optional AST analysis result for extra detail
        file: output file object (defaults to sys.stdout)
    """
    if file is None:
        file = sys.stdout

    try:
        import rich  # noqa: F401
        _render_rich(result, analysis, file)
    except ImportError:
        _render_plain(result, analysis, file)


def _render_rich(result: TestResult, analysis: AnalysisResult | None, file) -> None:
    """Render with rich library."""
    from rich.console import Console
    console = Console(file=file, force_terminal=False)

    # Header
    console.print()
    console.rule(f"[bold]selftest — {result.file_path}[/bold]")
    console.print()

    # Analysis summary
    if analysis:
        total_funcs = len(analysis.functions)
        total_branches = sum(len(f.branches) for f in analysis.functions)
        total_calls = sum(len(f.external_calls) for f in analysis.functions)
        total_randoms = sum(len(f.random_variables) for f in analysis.functions)

        console.print(f"[bold][1/4] AST 分析[/bold]")
        console.print(f"  [green]✓[/green] {total_funcs} 個函式, {total_branches} 個分支, {total_calls} 個外部呼叫")
        if total_randoms:
            console.print(f"  [green]✓[/green] 隨機變數: {total_randoms} 個")
        total_paths = sum(f.total_paths for f in analysis.functions)
        console.print(f"  [green]✓[/green] 預估需覆蓋路徑: {total_paths} 條")
        console.print()

    # Rule violations
    if result.rule_violations:
        console.print(f"[bold][2/4] 靜態規則檢查[/bold]")
        errors = [v for v in result.rule_violations if v.severity == "error"]
        warnings = [v for v in result.rule_violations if v.severity == "warning"]
        if errors:
            console.print(f"  [red]✗[/red] {len(errors)} errors, {len(warnings)} warnings")
        for v in result.rule_violations:
            color = "red" if v.severity == "error" else "yellow"
            console.print(f"    [{color}]L{v.line}: {v.description} [{v.severity}][/{color}]")
        console.print()

    # Test results
    console.print(f"[bold][4/4] 測試執行[/bold]")
    if result.passed > 0:
        console.print(f"  [green]✓ {result.passed} passed[/green]", end="")
    if result.failed > 0:
        console.print(f", [red]✗ {result.failed} failed[/red]", end="")
    if result.errors > 0:
        console.print(f", [red]! {result.errors} errors[/red]", end="")
    console.print()

    # Failed test details
    failed_tests = [d for d in result.details if d.status == "failed"]
    if failed_tests:
        console.print()
        console.print("  [bold red]FAILED:[/bold red]")
        for t in failed_tests:
            console.print(f"    [red]{t.test_name}[/red]:")
            if t.cause:
                console.print(f"      原因: {t.cause}")
            if t.suggestion:
                console.print(f"      建議: {t.suggestion}")
            if t.actual:
                console.print(f"      實際: {t.actual}")

    console.print()

    # Coverage
    cov = result.coverage
    color = "green" if cov.coverage_percent >= 80 else "yellow" if cov.coverage_percent >= 60 else "red"
    console.print(f"[{color}]覆蓋率: {cov.coverage_percent}% ({cov.covered_paths}/{cov.total_paths})[/{color}]")

    if cov.boundary_tests:
        boundary_ok = all(cov.boundary_tests.values())
        total = len(cov.boundary_tests)
        passed_count = sum(1 for v in cov.boundary_tests.values() if v)
        bcolor = "green" if boundary_ok else "yellow"
        console.print(f"[{bcolor}]邊界值: {passed_count}/{total} tested[/{bcolor}]")

    if result.rule_violations:
        errs = sum(1 for v in result.rule_violations if v.severity == "error")
        warns = sum(1 for v in result.rule_violations if v.severity == "warning")
        console.print(f"靜態規則: {errs + warns} issues ({errs} error, {warns} warning)")

    console.print()
    console.rule()


def _render_plain(result: TestResult, analysis: AnalysisResult | None, file) -> None:
    """Fallback plain text rendering."""
    w = file.write

    w(f"\n{'=' * 50}\n")
    w(f" selftest — {result.file_path}\n")
    w(f"{'=' * 50}\n\n")

    w(f"{result.passed} passed, {result.failed} failed, {result.errors} errors\n")

    for t in result.details:
        if t.status == "failed":
            w(f"\n  FAILED: {t.test_name}\n")
            if t.cause:
                w(f"    原因: {t.cause}\n")
            if t.suggestion:
                w(f"    建議: {t.suggestion}\n")

    cov = result.coverage
    w(f"\n覆蓋率: {cov.coverage_percent}% ({cov.covered_paths}/{cov.total_paths})\n")
    w(f"{'=' * 50}\n")
