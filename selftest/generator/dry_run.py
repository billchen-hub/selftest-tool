"""Generate basic test code for dry-run mode (no AI needed)."""

from __future__ import annotations

from selftest.models import AnalysisResult


def generate_dry_run_tests(analysis: AnalysisResult) -> str:
    """Generate basic pytest test code from analysis results.

    Produces a runnable test file that:
    - Mocks all imported modules
    - Calls each function inside try/except
    - Validates the pipeline ran through (not test quality)

    This is NOT meant to replace AI-generated tests. It exists to
    verify the pipeline works end-to-end without a real AI endpoint.
    """
    lines = [
        '"""Auto-generated dry-run tests (no AI). Verifies pipeline only."""',
        "",
        "import pytest",
        "from unittest.mock import MagicMock, patch",
        "import importlib.util",
        "import sys",
        "",
    ]

    source_path = analysis.file_path.replace("\\", "/")

    # Collect all modules that need to be mocked (both mock_targets and other imports)
    all_imports = set(analysis.imports)

    # Build a module loader fixture
    lines.append(f"SOURCE_PATH = r'{source_path}'")
    lines.append("")
    lines.append("")
    lines.append("def _load_module(name, mocks):")
    lines.append('    """Load source module with mocked dependencies."""')
    lines.append("    spec = importlib.util.spec_from_file_location(name, SOURCE_PATH)")
    lines.append("    mod = importlib.util.module_from_spec(spec)")
    lines.append("    saved = {}")
    lines.append("    for mod_name, mock_obj in mocks.items():")
    lines.append("        saved[mod_name] = sys.modules.get(mod_name)")
    lines.append("        sys.modules[mod_name] = mock_obj")
    lines.append("    try:")
    lines.append("        spec.loader.exec_module(mod)")
    lines.append("    finally:")
    lines.append("        for mod_name, prev in saved.items():")
    lines.append("            if prev is None:")
    lines.append("                sys.modules.pop(mod_name, None)")
    lines.append("            else:")
    lines.append("                sys.modules[mod_name] = prev")
    lines.append("    return mod")
    lines.append("")
    lines.append("")

    for func in analysis.functions:
        func_name = func.name
        params = func.params

        # Collect external call modules for this function
        ext_modules = set()
        for call in func.external_calls:
            ext_modules.add(call.module)

        # Build dummy args
        dummy_args = []
        for p in params:
            if p in ("self", "cls"):
                continue
            dummy_args.append("MagicMock()")
        args_str = ", ".join(dummy_args)

        lines.append(f"class TestDryRun_{func_name}:")
        lines.append(f'    """Dry-run tests for {func_name} ({func.total_paths} paths)."""')
        lines.append("")

        # Helper to build mocks dict
        lines.append(f"    @staticmethod")
        lines.append(f"    def _build_mocks():")
        lines.append(f"        mocks = {{}}")
        for mod in sorted(all_imports):
            lines.append(f"        mocks['{mod}'] = MagicMock()")
        lines.append(f"        return mocks")
        lines.append("")

        # Test 1: function can be imported and called
        lines.append(f"    def test_{func_name}_can_be_called(self):")
        lines.append(f'        """Pipeline check: {func_name} is importable and callable."""')
        lines.append(f"        mocks = self._build_mocks()")
        lines.append(f"        mod = _load_module('{func_name}_test', mocks)")
        lines.append(f"        assert hasattr(mod, '{func_name}')")
        lines.append(f"        assert callable(mod.{func_name})")
        lines.append("")

        # Test 2: happy path execution
        lines.append(f"    def test_{func_name}_happy_path(self):")
        lines.append(f'        """Pipeline check: {func_name} happy path executes."""')
        lines.append(f"        mocks = self._build_mocks()")

        # Set up realistic return values for known external calls
        for call in func.external_calls:
            mod_var = f"mocks['{call.module}']"
            lines.append(f"        {mod_var}.{call.method}.return_value = MagicMock(status=0, data=b'\\x00' * 32)")

        lines.append(f"        mod = _load_module('{func_name}_happy', mocks)")
        lines.append(f"        try:")
        lines.append(f"            result = mod.{func_name}({args_str})")
        lines.append(f"            # Function returned a value (did not raise)")
        lines.append(f"            assert result is not None or result is None")
        lines.append(f"        except Exception as e:")
        lines.append(f"            # Function raised — this is also a valid code path")
        lines.append(f"            assert isinstance(e, Exception)")
        lines.append("")

        # Test 3: analysis detected expected structures
        lines.append(f"    def test_{func_name}_analysis_structure(self):")
        lines.append(f'        """Pipeline check: AST analysis detected correct structure."""')
        lines.append(f"        # Branches detected: {len(func.branches)}")
        lines.append(f"        assert {len(func.branches)} >= 0  # branch count from analysis")
        lines.append(f"        # Total paths: {func.total_paths}")
        lines.append(f"        assert {func.total_paths} >= 1  # at least one path")
        lines.append(f"        # External calls: {len(func.external_calls)}")
        lines.append(f"        assert {len(func.external_calls)} >= 0")

        if func.random_variables:
            lines.append(f"        # Random variables: {len(func.random_variables)}")
            for rv in func.random_variables:
                if rv.boundary_values:
                    lines.append(f"        # {rv.name} boundary values: {rv.boundary_values}")
                    lines.append(f"        assert len({rv.boundary_values!r}) > 0")

        lines.append("")
        lines.append("")

    return "\n".join(lines)
