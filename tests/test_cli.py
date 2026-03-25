from pathlib import Path
from click.testing import CliRunner
from selftest.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "selftest" in result.output.lower() or "run" in result.output.lower()


def test_cli_analyze(fixtures_dir):
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Copy fixture
        Path("selftest.ini").write_text("""
[general]
mock_modules = tester
""", encoding="utf-8")
        result = runner.invoke(main, [
            "analyze",
            str(fixtures_dir / "branching_script.py"),
        ])
        assert result.exit_code == 0
        assert "verify_firmware_version" in result.output


def test_cli_analyze_nonexistent():
    runner = CliRunner()
    result = runner.invoke(main, ["analyze", "nonexistent.py"])
    assert result.exit_code != 0


def test_cli_clean():
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".selftest/tests").mkdir(parents=True)
        Path(".selftest/tests/old.py").write_text("old")
        result = runner.invoke(main, ["clean"])
        assert result.exit_code == 0
        assert "清理" in result.output


def test_cli_report_no_data():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["report", "nonexistent.py"])
        assert result.exit_code != 0
