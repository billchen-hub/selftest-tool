"""Static rules engine — load YAML rules and check source code."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from selftest.models import RuleViolation


_BUILTIN_RULES_PATH = Path(__file__).parent / "default_rules.yaml"


@dataclass
class Rule:
    id: str
    description: str
    severity: str  # "error" | "warning" | "disabled"
    pattern: str | None = None
    multiline: bool = False


def load_rules(
    builtin_path: Path | None = None,
    project_default_path: Path | None = None,
    project_custom_path: Path | None = None,
) -> list[Rule]:
    """Load rules from all sources with priority merging.

    Priority: project default overrides builtin (same id), custom adds new.
    """
    builtin = _load_rules_file(builtin_path or _BUILTIN_RULES_PATH)
    project_default = _load_rules_file(project_default_path) if project_default_path else []
    project_custom = _load_rules_file(project_custom_path) if project_custom_path else []

    # Index by id
    rules_map: dict[str, Rule] = {}
    for r in builtin:
        rules_map[r.id] = r
    for r in project_default:
        rules_map[r.id] = r  # override builtin
    for r in project_custom:
        rules_map[r.id] = r  # add or override

    # Filter out disabled rules
    return [r for r in rules_map.values() if r.severity != "disabled"]


def _load_rules_file(path: Path | None) -> list[Rule]:
    """Load rules from a single YAML file."""
    if path is None or not path.exists():
        return []

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError):
        return []

    if not isinstance(data, dict) or "rules" not in data:
        return []

    rules = []
    for entry in data["rules"]:
        match = entry.get("match", {})
        rules.append(Rule(
            id=entry["id"],
            description=entry.get("description", ""),
            severity=entry.get("severity", "warning"),
            pattern=match.get("pattern"),
            multiline=match.get("multiline", False),
        ))
    return rules


def check_rules(
    source: str,
    file_path: str,
    rules: list[Rule],
) -> list[RuleViolation]:
    """Check source code against rules and return violations.

    Args:
        source: Python source code
        file_path: path to the file (for reporting)
        rules: list of rules to check

    Returns:
        List of RuleViolation for each match
    """
    violations = []
    lines = source.splitlines()

    for rule in rules:
        if not rule.pattern:
            continue

        if rule.multiline:
            # Match against full source
            flags = re.MULTILINE
            for m in re.finditer(rule.pattern, source, flags):
                line_num = source[:m.start()].count("\n") + 1
                snippet = m.group(0).strip()[:80]
                violations.append(RuleViolation(
                    rule_id=rule.id,
                    description=rule.description,
                    severity=rule.severity,
                    file_path=file_path,
                    line=line_num,
                    code_snippet=snippet,
                    suggestion=f"違反規則: {rule.description}",
                ))
        else:
            # Match line by line
            compiled = re.compile(rule.pattern)
            for i, line in enumerate(lines, 1):
                if compiled.search(line):
                    violations.append(RuleViolation(
                        rule_id=rule.id,
                        description=rule.description,
                        severity=rule.severity,
                        file_path=file_path,
                        line=i,
                        code_snippet=line.strip()[:80],
                        suggestion=f"違反規則: {rule.description}",
                    ))

    return violations
