"""Parse AI response into valid pytest file and validate assertion quality."""

from __future__ import annotations

import ast
import re


def parse_ai_response(response: str) -> str:
    """Extract Python code from AI response.

    Tries to extract from ```python blocks first,
    falls back to treating entire response as code.
    """
    # Try to extract from markdown code blocks
    pattern = r'```python\s*\n(.*?)```'
    matches = re.findall(pattern, response, re.DOTALL)
    if matches:
        code = "\n\n".join(matches)
        # Verify it's valid Python
        try:
            ast.parse(code)
            return code.strip()
        except SyntaxError:
            pass

    # Try the whole response as code
    cleaned = response.strip()
    # Remove any markdown artifacts
    cleaned = re.sub(r'^```\w*\s*$', '', cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    try:
        ast.parse(cleaned)
        return cleaned
    except SyntaxError:
        pass

    # Last resort: return what we have, let the caller handle the error
    if matches:
        return matches[0].strip()
    return cleaned


_WEAK_ASSERTION_PATTERNS = [
    re.compile(r'\bassert\s+True\b'),
    re.compile(r'\bassert\s+\w+\s+is\s+not\s+None\b'),
    re.compile(r'\bassert\s+isinstance\s*\('),
    re.compile(r'\bassert\s+len\s*\(.+\)\s*>\s*0\b'),
]


def validate_test_code(code: str) -> list[str]:
    """Validate assertion quality in generated test code.

    Returns list of issues found. Empty list = good quality.
    """
    issues = []

    # Check for syntax validity
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"Syntax error: {e}"]

    # Find all test functions
    test_funcs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            test_funcs.append(node)

    if not test_funcs:
        issues.append("No test functions found (functions starting with test_)")
        return issues

    for func in test_funcs:
        func_source = ast.get_source_segment(code, func)
        if func_source is None:
            continue

        # Check for weak assertions
        for pattern in _WEAK_ASSERTION_PATTERNS:
            if pattern.search(func_source):
                issues.append(
                    f"Weak assertion in {func.name}: matches pattern '{pattern.pattern}'"
                )

        # Check that function has at least one assert or pytest.raises
        has_assert = False
        for child in ast.walk(func):
            if isinstance(child, ast.Assert):
                has_assert = True
                break
            # Check for pytest.raises in with statements
            if isinstance(child, ast.With):
                for item in child.items:
                    ctx = item.context_expr
                    if isinstance(ctx, ast.Call) and isinstance(ctx.func, ast.Attribute):
                        if ctx.func.attr == "raises":
                            has_assert = True
                            break

        if not has_assert:
            issues.append(f"No assertions found in {func.name}")

    return issues
