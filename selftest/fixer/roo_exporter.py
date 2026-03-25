"""Generate Roo Code instruction files from test results."""

from __future__ import annotations

from pathlib import Path

from selftest.models import TestResult, AnalysisResult


def export_roo_instruction(
    result: TestResult,
    analysis: AnalysisResult | None,
    target_file: Path,
    output_path: Path,
) -> Path:
    """Generate a Roo Code instruction file for fixing failed tests.

    Args:
        result: test execution result
        analysis: optional AST analysis result
        target_file: the original source file
        output_path: where to write the instruction .md file

    Returns:
        Path to the generated instruction file
    """
    lines = [f"# selftest 修改指令 — {target_file.name}\n"]
    lines.append(f"請修改 `{target_file}`，根據以下 selftest 分析結果：\n")

    issue_num = 1

    # Failed tests
    failed = [d for d in result.details if d.status == "failed"]
    if failed:
        lines.append("## 測試失敗\n")
        for f in failed:
            lines.append(f"### 問題 {issue_num}: {f.test_name}")
            if f.path_description:
                lines.append(f"- 路徑: {f.path_description}")
            if f.cause:
                lines.append(f"- 原因: {f.cause}")
            if f.actual:
                lines.append(f"- 實際行為: {f.actual}")
            if f.expected:
                lines.append(f"- 期望行為: {f.expected}")
            if f.suggestion:
                lines.append(f"- 建議修改: {f.suggestion}")
            if f.line_range:
                lines.append(f"- 相關行數: L{f.line_range[0]}-L{f.line_range[1]}")
            lines.append("")
            issue_num += 1

    # Rule violations
    errors = [v for v in result.rule_violations if v.severity == "error"]
    if errors:
        lines.append("## 靜態規則違反\n")
        for v in errors:
            lines.append(f"### 問題 {issue_num}: L{v.line} — {v.description}")
            lines.append(f"- 程式碼: `{v.code_snippet}`")
            lines.append(f"- 建議: {v.suggestion}")
            lines.append("")
            issue_num += 1

    # Constraints
    lines.append("## 修改注意事項\n")
    lines.append("- 不要改動函式的回傳值型別")
    lines.append("- 不要改動現有的 import 結構")
    lines.append("- 保持原有的 log 訊息格式")
    if analysis and analysis.mock_targets:
        lines.append(f"- 不要改動 {', '.join(analysis.mock_targets)} 的呼叫方式")

    content = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path
