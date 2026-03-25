"""Extract branches and paths from Python source using AST."""

from __future__ import annotations

import ast
from selftest.models import FunctionInfo, Branch, FunctionCall


def _count_paths(branches: list[Branch]) -> int:
    """Total path count = product of path counts at each branch point."""
    if not branches:
        return 1
    result = 1
    for b in branches:
        result *= len(b.paths)
    return result


def _extract_return_types(node: ast.FunctionDef) -> list[str]:
    """Infer return types from return statements and raise statements."""
    types = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Return):
            if child.value is None:
                types.add("None")
            elif isinstance(child.value, ast.Constant):
                types.add(type(child.value.value).__name__)
            else:
                types.add("unknown")
        elif isinstance(child, ast.Raise):
            if child.exc:
                if isinstance(child.exc, ast.Call) and isinstance(child.exc.func, ast.Name):
                    types.add(f"raises {child.exc.func.id}")
                elif isinstance(child.exc, ast.Name):
                    types.add(f"raises {child.exc.id}")
    return sorted(types) if types else ["None"]


def _extract_external_calls(node: ast.FunctionDef) -> list[FunctionCall]:
    """Extract all attribute-based calls like tester.send_cmd(...)."""
    calls = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            func = child.func
            if isinstance(func.value, ast.Name):
                module = func.value.id
                method = func.attr
                args = []
                for arg in child.args:
                    if isinstance(arg, ast.Constant):
                        args.append(repr(arg.value))
                    elif isinstance(arg, ast.Name):
                        args.append(arg.id)
                    else:
                        args.append("...")
                calls.append(FunctionCall(
                    module=module, method=method, args=args, line=child.lineno,
                ))
    return calls


def _format_condition(node: ast.expr) -> str:
    """Convert an AST expression to a readable condition string."""
    return ast.unparse(node)


def _extract_branches_from_body(body: list[ast.stmt]) -> list[Branch]:
    """Recursively extract branches from a list of statements."""
    branches = []
    for stmt in body:
        if isinstance(stmt, ast.If):
            condition = _format_condition(stmt.test)
            paths = [f"True (L{stmt.lineno})"]
            # count elif branches
            current = stmt
            while current.orelse:
                if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                    elif_node = current.orelse[0]
                    elif_cond = _format_condition(elif_node.test)
                    paths.append(f"{elif_cond} (L{elif_node.lineno})")
                    current = elif_node
                else:
                    paths.append(f"else (L{current.orelse[0].lineno})")
                    break
            if not stmt.orelse:
                paths.append("no else (implicit)")

            branches.append(Branch(condition=condition, line=stmt.lineno, paths=paths))

            # recurse into if/elif/else bodies
            branches.extend(_extract_branches_from_body(stmt.body))
            current = stmt
            while current.orelse:
                if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                    branches.extend(_extract_branches_from_body(current.orelse[0].body))
                    current = current.orelse[0]
                else:
                    branches.extend(_extract_branches_from_body(current.orelse))
                    break

        elif isinstance(stmt, ast.Try):
            handler_paths = []
            for handler in stmt.handlers:
                if handler.type:
                    handler_paths.append(f"except {ast.unparse(handler.type)} (L{handler.lineno})")
                else:
                    handler_paths.append(f"except (bare) (L{handler.lineno})")
            if handler_paths:
                branches.append(Branch(
                    condition="try/except", line=stmt.lineno, paths=["try body"] + handler_paths,
                ))

        elif isinstance(stmt, ast.For):
            branches.extend(_extract_branches_from_body(stmt.body))
        elif isinstance(stmt, ast.While):
            branches.extend(_extract_branches_from_body(stmt.body))

    return branches


def extract_branches(source: str) -> list[FunctionInfo]:
    """Parse source code and extract branch info for each function."""
    tree = ast.parse(source)
    functions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            branches = _extract_branches_from_body(node.body)
            external_calls = _extract_external_calls(node)
            return_types = _extract_return_types(node)
            total_paths = _count_paths(branches)

            functions.append(FunctionInfo(
                name=node.name,
                params=[arg.arg for arg in node.args.args],
                external_calls=external_calls,
                branches=branches,
                total_paths=total_paths,
                return_types=return_types,
            ))

    return functions
