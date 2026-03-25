"""Generate HTML reports using Jinja2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from selftest.models import TestResult


_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


@dataclass
class SourceLine:
    num: int
    text: str
    css_class: str  # "line-covered" | "line-uncovered" | ""


def generate_html_report(
    result: TestResult,
    output_path: Path,
    source_file: Path | None = None,
) -> Path:
    """Generate an HTML report from test results.

    Args:
        result: test execution result
        output_path: where to write the HTML file
        source_file: original source file (for coverage coloring)

    Returns:
        Path to the generated HTML file
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("report.html.j2")

    # Prepare source lines with coverage coloring
    source_lines = []
    if source_file and source_file.exists():
        uncovered = set(result.coverage.uncovered_lines)
        for i, line_text in enumerate(source_file.read_text(encoding="utf-8").splitlines(), 1):
            if uncovered and i in uncovered:
                css = "line-uncovered"
            elif uncovered:
                css = "line-covered"
            else:
                css = ""
            source_lines.append(SourceLine(num=i, text=line_text, css_class=css))

    failed_tests = [d for d in result.details if d.status == "failed"]

    from selftest import __version__
    html = template.render(
        result=result,
        failed_tests=failed_tests,
        source_lines=source_lines,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        version=__version__,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
