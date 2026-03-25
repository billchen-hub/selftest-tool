"""Detect random variables and derive boundary values."""

from __future__ import annotations

import ast
from selftest.models import RandomVar


def _find_comparisons_involving(tree: ast.AST, var_name: str) -> list[tuple[str, float | None]]:
    """Find all comparisons involving var_name and extract threshold values."""
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            condition_str = ast.unparse(node)
            if var_name in condition_str:
                # Extract numeric comparators
                for comparator in node.comparators:
                    if isinstance(comparator, ast.Constant) and isinstance(comparator.value, (int, float)):
                        results.append((condition_str, comparator.value))
                # Also check the left side
                if isinstance(node.left, ast.Constant) and isinstance(node.left.value, (int, float)):
                    results.append((condition_str, node.left.value))
    return results


def _derive_boundary_values(
    range_min: float | None,
    range_max: float | None,
    thresholds: list[float],
) -> list:
    """Derive boundary values from range and thresholds."""
    values = set()

    if range_min is not None:
        values.add(range_min)
    if range_max is not None:
        values.add(range_max)

    for t in thresholds:
        values.add(t)
        if isinstance(t, int):
            values.add(t - 1)
            values.add(t + 1)
        else:
            values.add(t - 0.001)
            values.add(t + 0.001)

    # Add a midpoint
    if range_min is not None and range_max is not None:
        mid = (range_min + range_max) / 2
        if isinstance(range_min, int) and isinstance(range_max, int):
            mid = int(mid)
        values.add(mid)

    # Filter to within range
    if range_min is not None and range_max is not None:
        values = {v for v in values if range_min <= v <= range_max}

    return sorted(values)


def detect_random_vars(source: str) -> list[RandomVar]:
    """Detect random variable assignments and derive boundary values."""
    tree = ast.parse(source)
    randoms = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue

        var_name = node.targets[0].id
        value = node.value

        # Check for random.randint(a, b)
        if (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
                and isinstance(value.func.value, ast.Name)
                and value.func.value.id == "random"
                and value.func.attr == "randint"
                and len(value.args) == 2):
            a, b = value.args
            if isinstance(a, ast.Constant) and isinstance(b, ast.Constant):
                range_min = a.value
                range_max = b.value
                comparisons = _find_comparisons_involving(tree, var_name)
                thresholds = [t for _, t in comparisons if t is not None]
                affects = [cond for cond, _ in comparisons]
                boundary_values = _derive_boundary_values(range_min, range_max, thresholds)

                randoms.append(RandomVar(
                    name=var_name,
                    source=ast.unparse(value),
                    range_min=range_min,
                    range_max=range_max,
                    enum_values=None,
                    affects_branches=affects,
                    boundary_values=boundary_values,
                ))

        # Check for random.choice([...])
        elif (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
              and isinstance(value.func.value, ast.Name)
              and value.func.value.id == "random"
              and value.func.attr == "choice"
              and len(value.args) == 1
              and isinstance(value.args[0], ast.List)):
            enum_vals = []
            for elt in value.args[0].elts:
                if isinstance(elt, ast.Constant):
                    enum_vals.append(elt.value)
            if enum_vals:
                randoms.append(RandomVar(
                    name=var_name,
                    source=ast.unparse(value),
                    range_min=None,
                    range_max=None,
                    enum_values=enum_vals,
                    affects_branches=[],
                    boundary_values=enum_vals,
                ))

        # Check for random.uniform(a, b)
        elif (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
              and isinstance(value.func.value, ast.Name)
              and value.func.value.id == "random"
              and value.func.attr == "uniform"
              and len(value.args) == 2):
            a, b = value.args
            if isinstance(a, ast.Constant) and isinstance(b, ast.Constant):
                range_min = float(a.value)
                range_max = float(b.value)
                comparisons = _find_comparisons_involving(tree, var_name)
                thresholds = [t for _, t in comparisons if t is not None]
                affects = [cond for cond, _ in comparisons]
                boundary_values = _derive_boundary_values(range_min, range_max, thresholds)

                randoms.append(RandomVar(
                    name=var_name,
                    source=ast.unparse(value),
                    range_min=range_min,
                    range_max=range_max,
                    enum_values=None,
                    affects_branches=affects,
                    boundary_values=boundary_values,
                ))

    return randoms
