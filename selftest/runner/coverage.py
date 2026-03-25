"""Parse coverage data from pytest-cov output."""

from __future__ import annotations

import json
from pathlib import Path

from selftest.models import CoverageInfo


def parse_coverage_json(coverage_json_path: Path, source_file: str) -> CoverageInfo | None:
    """Parse coverage.json from pytest-cov and return CoverageInfo."""
    if not coverage_json_path.exists():
        return None

    data = json.loads(coverage_json_path.read_text(encoding="utf-8"))

    # Find the source file in coverage data
    files = data.get("files", {})
    for file_key, file_data in files.items():
        if source_file in file_key or file_key in source_file:
            summary = file_data.get("summary", {})
            missing_lines = file_data.get("missing_lines", [])
            covered = summary.get("covered_lines", 0)
            total = summary.get("num_statements", 0)
            percent = summary.get("percent_covered", 0.0)

            return CoverageInfo(
                total_paths=total,
                covered_paths=covered,
                coverage_percent=round(percent, 1),
                uncovered_lines=missing_lines,
                boundary_tests={},
            )

    return None
