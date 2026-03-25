from selftest.generator.prompt_builder import build_prompt
from selftest.models import AnalysisResult, FunctionInfo, Branch, FunctionCall, RandomVar


def test_build_prompt_includes_analysis():
    analysis = AnalysisResult(
        file_path="test.py",
        functions=[FunctionInfo(
            name="my_func", params=["device"],
            external_calls=[FunctionCall("tester", "send_cmd", ["READ"], 5)],
            branches=[Branch("resp.status != 0", 6, ["True", "False"])],
            total_paths=2, return_types=["bool"], random_variables=[],
        )],
        imports=["tester"], mock_targets=["tester"],
    )
    prompt = build_prompt(analysis, user_prompts_dir=None)
    assert "my_func" in prompt
    assert "tester.send_cmd" in prompt
    assert "resp.status != 0" in prompt
    assert "2" in prompt  # total_paths


def test_build_prompt_includes_random_vars():
    analysis = AnalysisResult(
        file_path="test.py",
        functions=[FunctionInfo(
            name="foo", params=["x"],
            external_calls=[], branches=[], total_paths=1,
            return_types=["int"],
            random_variables=[RandomVar(
                name="addr", source="random.randint(0, 100)",
                range_min=0, range_max=100,
                boundary_values=[0, 50, 100],
            )],
        )],
        imports=[], mock_targets=[],
    )
    prompt = build_prompt(analysis)
    assert "addr" in prompt
    assert "random.randint(0, 100)" in prompt
    assert "[0, 50, 100]" in prompt


def test_build_prompt_includes_user_rules(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "custom.md").write_text("Always check timeout parameter.")

    analysis = AnalysisResult(
        file_path="test.py", functions=[], imports=[], mock_targets=[],
    )
    prompt = build_prompt(analysis, user_prompts_dir=prompts_dir)
    assert "Always check timeout parameter" in prompt


def test_build_prompt_sorts_user_rules(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "_base.md").write_text("BASE RULE")
    (prompts_dir / "z_last.md").write_text("LAST RULE")
    (prompts_dir / "a_first.md").write_text("FIRST RULE")

    analysis = AnalysisResult(
        file_path="test.py", functions=[], imports=[], mock_targets=[],
    )
    prompt = build_prompt(analysis, user_prompts_dir=prompts_dir)
    # _base.md should come before a_first.md, a_first before z_last
    base_pos = prompt.index("BASE RULE")
    first_pos = prompt.index("FIRST RULE")
    last_pos = prompt.index("LAST RULE")
    assert base_pos < first_pos < last_pos
