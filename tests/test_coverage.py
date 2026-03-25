import json
from selftest.runner.coverage import parse_coverage_json


def test_parse_coverage_json(tmp_path):
    cov_data = {
        "files": {
            "scripts/test_case.py": {
                "summary": {
                    "covered_lines": 15,
                    "num_statements": 20,
                    "percent_covered": 75.0,
                },
                "missing_lines": [5, 10, 15, 18, 19],
            }
        }
    }
    cov_file = tmp_path / "coverage.json"
    cov_file.write_text(json.dumps(cov_data), encoding="utf-8")

    result = parse_coverage_json(cov_file, "test_case.py")
    assert result is not None
    assert result.covered_paths == 15
    assert result.total_paths == 20
    assert result.coverage_percent == 75.0
    assert result.uncovered_lines == [5, 10, 15, 18, 19]


def test_parse_coverage_json_missing_file(tmp_path):
    result = parse_coverage_json(tmp_path / "nonexistent.json", "test.py")
    assert result is None


def test_parse_coverage_json_no_matching_source(tmp_path):
    cov_data = {"files": {"other_file.py": {"summary": {}}}}
    cov_file = tmp_path / "coverage.json"
    cov_file.write_text(json.dumps(cov_data), encoding="utf-8")

    result = parse_coverage_json(cov_file, "not_in_coverage.py")
    assert result is None
