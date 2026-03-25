"""Data models — contracts between all selftest modules."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


# ---------------------------------------------------------------------------
# AST analysis models
# ---------------------------------------------------------------------------

@dataclass
class FunctionCall:
    module: str
    method: str
    args: list[str]
    line: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> FunctionCall:
        return cls(**d)


@dataclass
class Branch:
    condition: str
    line: int
    paths: list[str]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Branch:
        return cls(**d)


@dataclass
class RandomVar:
    name: str
    source: str
    range_min: float | None = None
    range_max: float | None = None
    enum_values: list | None = None
    affects_branches: list[str] = field(default_factory=list)
    boundary_values: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> RandomVar:
        return cls(**d)


@dataclass
class FunctionInfo:
    name: str
    params: list[str]
    external_calls: list[FunctionCall]
    branches: list[Branch]
    total_paths: int
    return_types: list[str]
    random_variables: list[RandomVar] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "params": self.params,
            "external_calls": [c.to_dict() for c in self.external_calls],
            "branches": [b.to_dict() for b in self.branches],
            "total_paths": self.total_paths,
            "return_types": self.return_types,
            "random_variables": [r.to_dict() for r in self.random_variables],
        }

    @classmethod
    def from_dict(cls, d: dict) -> FunctionInfo:
        return cls(
            name=d["name"],
            params=d["params"],
            external_calls=[FunctionCall.from_dict(c) for c in d["external_calls"]],
            branches=[Branch.from_dict(b) for b in d["branches"]],
            total_paths=d["total_paths"],
            return_types=d["return_types"],
            random_variables=[RandomVar.from_dict(r) for r in d.get("random_variables", [])],
        )


@dataclass
class AnalysisResult:
    file_path: str
    functions: list[FunctionInfo]
    imports: list[str]
    mock_targets: list[str]

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "functions": [f.to_dict() for f in self.functions],
            "imports": self.imports,
            "mock_targets": self.mock_targets,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AnalysisResult:
        return cls(
            file_path=d["file_path"],
            functions=[FunctionInfo.from_dict(f) for f in d["functions"]],
            imports=d["imports"],
            mock_targets=d["mock_targets"],
        )


# ---------------------------------------------------------------------------
# Rule violation
# ---------------------------------------------------------------------------

@dataclass
class RuleViolation:
    rule_id: str
    description: str
    severity: str  # "error" | "warning"
    file_path: str
    line: int
    code_snippet: str
    suggestion: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> RuleViolation:
        return cls(**d)


# ---------------------------------------------------------------------------
# Test execution results
# ---------------------------------------------------------------------------

@dataclass
class SingleTestResult:
    test_name: str
    path_description: str
    status: str  # "passed" | "failed" | "error"
    expected: str | None = None
    actual: str | None = None
    traceback: str | None = None
    cause: str | None = None
    suggestion: str | None = None
    line_range: tuple[int, int] | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.line_range is not None:
            d["line_range"] = list(self.line_range)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> SingleTestResult:
        d = dict(d)
        if d.get("line_range") is not None:
            d["line_range"] = tuple(d["line_range"])
        return cls(**d)


@dataclass
class CoverageInfo:
    total_paths: int
    covered_paths: int
    coverage_percent: float
    uncovered_lines: list[int]
    boundary_tests: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> CoverageInfo:
        return cls(**d)


@dataclass
class TestResult:
    __test__ = False  # prevent pytest from collecting this as a test class

    file_path: str
    generated_test_path: str
    passed: int
    failed: int
    errors: int
    details: list[SingleTestResult]
    coverage: CoverageInfo
    rule_violations: list[RuleViolation]
    assertion_quality_ok: bool
    verification_rounds: int

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "generated_test_path": self.generated_test_path,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "details": [d.to_dict() for d in self.details],
            "coverage": self.coverage.to_dict(),
            "rule_violations": [v.to_dict() for v in self.rule_violations],
            "assertion_quality_ok": self.assertion_quality_ok,
            "verification_rounds": self.verification_rounds,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TestResult:
        return cls(
            file_path=d["file_path"],
            generated_test_path=d["generated_test_path"],
            passed=d["passed"],
            failed=d["failed"],
            errors=d["errors"],
            details=[SingleTestResult.from_dict(x) for x in d["details"]],
            coverage=CoverageInfo.from_dict(d["coverage"]),
            rule_violations=[RuleViolation.from_dict(v) for v in d["rule_violations"]],
            assertion_quality_ok=d["assertion_quality_ok"],
            verification_rounds=d["verification_rounds"],
        )
