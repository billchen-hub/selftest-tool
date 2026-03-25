"""CLI entry point for selftest tool."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import click

from selftest.config import load_config
from selftest.models import AnalysisResult, TestResult


def _find_config(config_path: str | None) -> Path:
    """Find selftest.ini, searching upward from cwd."""
    if config_path:
        return Path(config_path)
    # Search upward
    p = Path.cwd()
    while p != p.parent:
        candidate = p / "selftest.ini"
        if candidate.exists():
            return candidate
        p = p.parent
    return Path("selftest.ini")  # default, may not exist


def _ensure_selftest_dir(base: Path) -> Path:
    """Ensure .selftest directory structure exists."""
    selftest_dir = base / ".selftest"
    for sub in ["tests", "mocks", "reports", "coverage", "data",
                "patches", "backups", "roo", "rules/prompts", "rules/static",
                "cache", "logs"]:
        (selftest_dir / sub).mkdir(parents=True, exist_ok=True)
    return selftest_dir


@click.group()
@click.option("--config", "config_path", default=None, help="Path to selftest.ini")
@click.option("-v", "--verbose", count=True, help="Verbose output (-v, -vv)")
@click.pass_context
def main(ctx, config_path, verbose):
    """selftest — Auto-generate and run self-tests for Python scripts."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path
    ctx.obj["verbose"] = verbose


@main.command()
@click.pass_context
def init(ctx):
    """Initialize selftest in current directory."""
    cwd = Path.cwd()
    ini_path = cwd / "selftest.ini"

    if ini_path.exists():
        click.echo("selftest.ini already exists. Overwrite? [y/N] ", nl=False)
        if input().strip().lower() != "y":
            click.echo("Aborted.")
            return

    # Interactive setup
    click.echo("\nselftest 初始化精靈")
    click.echo("━" * 30)

    source_dirs = click.prompt("腳本目錄", default="scripts/")
    lib_dirs = click.prompt("共用 Lib 目錄", default="lib/")
    mock_modules = click.prompt("需要 mock 的模組 (逗號分隔)", default="tester")
    never_mock = click.prompt("不 mock 的模組 (逗號分隔, 可留空)", default="")

    click.echo("\nAI 設定:")
    provider = click.prompt("AI provider (local_llm / company_platform)", default="local_llm")

    ini_content = f"""[general]
source_dirs = {source_dirs}
lib_dirs = {lib_dirs}
mock_modules = {mock_modules}
never_mock = {never_mock}
coverage_threshold = 80

[ai]
provider = {provider}
"""

    if provider == "local_llm":
        endpoint = click.prompt("API endpoint", default="http://localhost:8080/v1")
        model = click.prompt("Model name", default="qwen-72b")
        api_key = click.prompt("API key (可留空)", default="")
        ini_content += f"""
[local_llm]
endpoint = {endpoint}
model = {model}
api_key = {api_key}
"""
    elif provider == "company_platform":
        base_url = click.prompt("Nexus API base URL", default="http://ainexus.phison.com:5155")
        api_key = click.prompt("API key")
        share_code = click.prompt("Share code (模型代號)")
        ini_content += f"""
[company_platform]
base_url = {base_url}
api_key = {api_key}
share_code = {share_code}
timeout = 120
"""

    ini_content += """
[report]
html_dir = .selftest/reports/
keep_days = 30
"""

    ini_path.write_text(ini_content, encoding="utf-8")
    click.echo(f"\n✓ 已建立 {ini_path}")

    # Create .selftest directory
    selftest_dir = _ensure_selftest_dir(cwd)
    click.echo(f"✓ 已建立 {selftest_dir}")

    # Create default prompt
    base_prompt = selftest_dir / "rules" / "prompts" / "_base.md"
    if not base_prompt.exists():
        from selftest.generator.prompt_builder import _load_base_template
        base_prompt.write_text(_load_base_template(), encoding="utf-8")
        click.echo(f"✓ 已建立 {base_prompt}")

    # Add to .gitignore
    gitignore = cwd / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if ".selftest/" not in content:
            with open(gitignore, "a", encoding="utf-8") as f:
                f.write("\n.selftest/\n")
            click.echo("✓ 已加入 .gitignore")
    else:
        gitignore.write_text(".selftest/\n", encoding="utf-8")
        click.echo("✓ 已建立 .gitignore")

    click.echo(f"\n可以開始使用: selftest run {source_dirs}/<your_script>.py")


@main.command()
@click.argument("target")
@click.pass_context
def analyze(ctx, target):
    """Analyze a Python file (AST only)."""
    from selftest.analyzer.ast_analyzer import analyze_file

    target_path = Path(target)
    if not target_path.exists():
        click.echo(f"Error: {target} not found", err=True)
        sys.exit(1)

    config_path = _find_config(ctx.obj.get("config_path"))
    config = load_config(config_path)

    result = analyze_file(target_path, config.mock_modules, config.never_mock)

    # Print summary
    click.echo(f"\n分析結果: {target}")
    click.echo(f"  函式數: {len(result.functions)}")
    for func in result.functions:
        click.echo(f"\n  {func.name}({', '.join(func.params)})")
        click.echo(f"    分支: {len(func.branches)}, 路徑: {func.total_paths}")
        click.echo(f"    外部呼叫: {len(func.external_calls)}")
        click.echo(f"    回傳型別: {', '.join(func.return_types)}")
        if func.random_variables:
            click.echo(f"    隨機變數: {len(func.random_variables)}")
            for rv in func.random_variables:
                click.echo(f"      - {rv.name}: {rv.source}")
                if rv.boundary_values:
                    click.echo(f"        邊界值: {rv.boundary_values}")

    click.echo(f"\n  需 mock: {', '.join(result.mock_targets) or '(無)'}")

    # Save analysis result
    selftest_dir = _ensure_selftest_dir(target_path.parent)
    data_dir = selftest_dir / "data"
    stem = target_path.stem
    out = data_dir / f"{stem}.analysis.json"
    out.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    click.echo(f"\n  已儲存: {out}")


@main.command()
@click.argument("target")
@click.option("--provider", default=None, help="Override AI provider")
@click.option("--rules-only", is_flag=True, help="Only run static rules, skip AI")
@click.option("--roo", is_flag=True, help="Generate Roo Code instruction file")
@click.option("--patch", is_flag=True, help="Generate patch file")
@click.pass_context
def run(ctx, target, provider, rules_only, roo, patch):
    """Run full self-test pipeline on a file or directory."""
    from selftest.analyzer.ast_analyzer import analyze_file
    from selftest.generator.ai_client import AIClient, AIProviderError
    from selftest.generator.prompt_builder import build_prompt
    from selftest.generator.test_builder import parse_ai_response, validate_test_code
    from selftest.generator.mock_factory import generate_mock_setup
    from selftest.runner.executor import run_tests
    from selftest.reporter.terminal import render_terminal_report

    target_path = Path(target)
    if not target_path.exists():
        click.echo(f"Error: {target} not found", err=True)
        sys.exit(1)

    # Handle directory
    if target_path.is_dir():
        py_files = sorted(target_path.glob("*.py"))
        if not py_files:
            click.echo(f"No .py files found in {target}")
            return
        for f in py_files:
            ctx.invoke(run, target=str(f), provider=provider,
                       rules_only=rules_only, roo=roo, patch=patch)
        return

    config_path = _find_config(ctx.obj.get("config_path"))
    config = load_config(config_path)
    if provider:
        config.ai_provider = provider

    project_dir = target_path.parent
    selftest_dir = _ensure_selftest_dir(project_dir)
    verbose = ctx.obj.get("verbose", 0)

    # Step 1: AST Analysis
    if verbose:
        click.echo(f"\n[1/4] AST 分析中... {target_path.name}")
    analysis = analyze_file(target_path, config.mock_modules, config.never_mock)

    # Step 2: Static rules check
    from selftest.rules.engine import load_rules, check_rules

    static_rules_dir = selftest_dir / "rules" / "static"
    rules = load_rules(
        project_default_path=static_rules_dir / "default.yaml" if (static_rules_dir / "default.yaml").exists() else None,
        project_custom_path=static_rules_dir / "custom.yaml" if (static_rules_dir / "custom.yaml").exists() else None,
    )
    source_text = target_path.read_text(encoding="utf-8")
    rule_violations = check_rules(source_text, str(target_path), rules)

    if verbose:
        errors = [v for v in rule_violations if v.severity == "error"]
        warnings = [v for v in rule_violations if v.severity == "warning"]
        if rule_violations:
            click.echo(f"[2/4] 靜態規則: {len(errors)} errors, {len(warnings)} warnings")
        else:
            click.echo(f"[2/4] 靜態規則: 全部通過")

    if rules_only:
        # In rules-only mode, render just the rule results
        from selftest.reporter.terminal import render_terminal_report
        from selftest.models import CoverageInfo
        rule_result = TestResult(
            file_path=str(target_path),
            generated_test_path="",
            passed=0, failed=0, errors=0,
            details=[],
            coverage=CoverageInfo(0, 0, 0.0, [], {}),
            rule_violations=rule_violations,
            assertion_quality_ok=True,
            verification_rounds=0,
        )
        render_terminal_report(rule_result, analysis=analysis)
        return

    # Step 3: Build prompt and call AI
    if verbose:
        click.echo("[3/4] AI 產生測試碼...")

    prompts_dir = selftest_dir / "rules" / "prompts"
    prompt = build_prompt(analysis, user_prompts_dir=prompts_dir if prompts_dir.exists() else None)

    try:
        ai_config = {}
        if config.ai_provider == "local_llm":
            ai_config = config.local_llm
        elif config.ai_provider == "company_platform":
            ai_config = config.company_platform
        ai_config["max_response_tokens"] = str(config.max_response_tokens)

        client = AIClient(provider=config.ai_provider, config=ai_config)
        ai_response = client.generate(prompt)
    except (AIProviderError, ConnectionError, Exception) as e:
        click.echo(f"\n⚠ AI 呼叫失敗: {e}", err=True)
        click.echo("降級為靜態規則模式", err=True)
        return

    # Step 3: Parse and validate test code
    test_code = parse_ai_response(ai_response)
    quality_issues = validate_test_code(test_code)

    # Add mock setup
    mock_code = generate_mock_setup(analysis)
    full_test_code = mock_code + "\n\n" + test_code

    # Write test file
    stem = target_path.stem
    test_file = selftest_dir / "tests" / f"test__{stem}.py"
    test_file.write_text(full_test_code, encoding="utf-8")

    if verbose:
        click.echo(f"  ✓ 測試碼已寫入: {test_file}")
        if quality_issues:
            click.echo(f"  ⚠ 斷言品質問題: {len(quality_issues)}")

    # Step 4: Run tests
    if verbose:
        click.echo("[4/4] 執行測試...")

    test_result = run_tests(test_file, source_file=target_path, selftest_dir=selftest_dir)
    test_result.assertion_quality_ok = len(quality_issues) == 0
    test_result.rule_violations = rule_violations

    # Save result
    data_dir = selftest_dir / "data"
    result_file = data_dir / f"{stem}.result.json"
    result_file.write_text(
        json.dumps(test_result.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Render terminal report
    render_terminal_report(test_result, analysis=analysis)

    # Generate HTML report
    from selftest.reporter.html import generate_html_report
    html_dir = selftest_dir / "reports"
    html_file = html_dir / f"{datetime.now().strftime('%Y-%m-%d')}_{stem}.html"
    generate_html_report(test_result, html_file, source_file=target_path)
    click.echo(f"\nHTML 報告: {html_file}")

    # Generate Roo Code instruction if requested
    if roo:
        from selftest.fixer.roo_exporter import export_roo_instruction
        roo_file = selftest_dir / "roo" / f"fix_{stem}.md"
        export_roo_instruction(test_result, analysis, target_path, roo_file)
        click.echo(f"Roo Code 指令檔: {roo_file}")


@main.command()
@click.argument("target")
@click.pass_context
def report(ctx, target):
    """Regenerate report from saved results."""
    from selftest.reporter.terminal import render_terminal_report

    target_path = Path(target)
    stem = target_path.stem
    selftest_dir = _ensure_selftest_dir(target_path.parent)

    result_file = selftest_dir / "data" / f"{stem}.result.json"
    if not result_file.exists():
        click.echo(f"No saved results for {target}. Run 'selftest run' first.", err=True)
        sys.exit(1)

    from selftest.models import TestResult
    data = json.loads(result_file.read_text(encoding="utf-8"))
    test_result = TestResult.from_dict(data)

    # Try to load analysis
    analysis = None
    analysis_file = selftest_dir / "data" / f"{stem}.analysis.json"
    if analysis_file.exists():
        analysis_data = json.loads(analysis_file.read_text(encoding="utf-8"))
        analysis = AnalysisResult.from_dict(analysis_data)

    render_terminal_report(test_result, analysis=analysis)


@main.command()
@click.pass_context
def clean(ctx):
    """Clean up expired selftest files."""
    cwd = Path.cwd()
    selftest_dir = cwd / ".selftest"
    if not selftest_dir.exists():
        click.echo("No .selftest directory found.")
        return

    import shutil
    for sub in ["tests", "reports", "coverage", "data", "patches", "backups", "cache", "logs"]:
        d = selftest_dir / sub
        if d.exists():
            count = len(list(d.iterdir()))
            if count:
                shutil.rmtree(d)
                d.mkdir()
                click.echo(f"  ✓ 清理 {sub}/ ({count} 個檔案)")

    click.echo("清理完成")


@main.command()
@click.argument("target")
@click.pass_context
def fix(ctx, target):
    """Interactively apply suggested fixes from selftest results."""
    from selftest.fixer.patch_generator import generate_patches, format_diff
    from selftest.fixer.interactive_apply import apply_patches

    target_path = Path(target)
    if not target_path.exists():
        click.echo(f"Error: {target} not found", err=True)
        sys.exit(1)

    stem = target_path.stem
    selftest_dir = _ensure_selftest_dir(target_path.parent)

    # Load saved result
    result_file = selftest_dir / "data" / f"{stem}.result.json"
    if not result_file.exists():
        click.echo(f"No saved results for {target}. Run 'selftest run' first.", err=True)
        sys.exit(1)

    data = json.loads(result_file.read_text(encoding="utf-8"))
    test_result = TestResult.from_dict(data)

    patches = generate_patches(test_result, target_path)
    if not patches:
        click.echo("沒有建議修改")
        return

    click.echo(f"\n找到 {len(patches)} 個建議修改:\n")
    for p in patches:
        click.echo(format_diff(p))
        click.echo()

    choice = click.prompt(
        "套用哪些？ [A]全部 / 輸入編號(逗號分隔) / [N]取消",
        default="N",
    )

    if choice.upper() == "N":
        click.echo("已取消")
        return

    if choice.upper() == "A":
        selected = None  # all
    else:
        try:
            selected = [int(x.strip()) for x in choice.split(",")]
        except ValueError:
            click.echo("無效的輸入")
            return

    backup_dir = selftest_dir / "backups"
    applied = apply_patches(patches, target_path, backup_dir, selected_indices=selected)

    if applied:
        click.echo(f"\n✓ 已套用 {len(applied)} 個修改")
        click.echo(f"  備份: {backup_dir / target_path.name}.bak")
    else:
        click.echo("沒有套用任何修改")


if __name__ == "__main__":
    main()
