"""Main AST analysis orchestrator — combines all sub-analyzers."""

from __future__ import annotations

from pathlib import Path

from selftest.models import AnalysisResult
from selftest.analyzer.branch_extractor import extract_branches
from selftest.analyzer.import_resolver import resolve_imports
from selftest.analyzer.random_detector import detect_random_vars


def analyze_file(
    file_path: Path,
    mock_modules: list[str] | None = None,
    never_mock: list[str] | None = None,
) -> AnalysisResult:
    """Analyze a Python file and return structured analysis result.

    Args:
        file_path: path to the Python file
        mock_modules: modules to always mock
        never_mock: modules to never mock

    Returns:
        AnalysisResult with functions, imports, and mock targets
    """
    if mock_modules is None:
        mock_modules = []
    if never_mock is None:
        never_mock = []

    source = Path(file_path).read_text(encoding="utf-8")

    # Extract function info (branches, calls, return types)
    functions = extract_branches(source)

    # Resolve imports
    import_result = resolve_imports(source, mock_modules, never_mock)

    # Detect random variables and attach to functions
    random_vars = detect_random_vars(source)
    # Attach random vars to the functions they belong to (by line range heuristic)
    # For now, attach all random vars to all functions that contain them
    if random_vars:
        import ast
        tree = ast.parse(source)
        for func_node in ast.walk(tree):
            if not isinstance(func_node, ast.FunctionDef):
                continue
            func_start = func_node.lineno
            func_end = func_node.end_lineno or func_start + 1000

            matching_func = None
            for fi in functions:
                if fi.name == func_node.name:
                    matching_func = fi
                    break

            if matching_func is None:
                continue

            for rv in random_vars:
                # Find the assignment line for this random var
                for node in ast.walk(func_node):
                    if (isinstance(node, ast.Assign)
                            and len(node.targets) == 1
                            and isinstance(node.targets[0], ast.Name)
                            and node.targets[0].id == rv.name):
                        if func_start <= node.lineno <= func_end:
                            if rv not in matching_func.random_variables:
                                matching_func.random_variables.append(rv)

    return AnalysisResult(
        file_path=str(file_path),
        functions=functions,
        imports=import_result.all_imports,
        mock_targets=import_result.mock_targets,
    )
