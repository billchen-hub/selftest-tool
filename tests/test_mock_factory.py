from selftest.generator.mock_factory import generate_mock_setup
from selftest.models import AnalysisResult, FunctionInfo, FunctionCall


def test_generate_mock_for_tester():
    analysis = AnalysisResult(
        file_path="scripts/test_case.py",
        functions=[FunctionInfo(
            name="verify", params=["device"],
            external_calls=[
                FunctionCall("tester", "send_cmd", ["GET_VERSION", "device"], 5),
            ],
            branches=[], total_paths=1, return_types=["bool"],
            random_variables=[],
        )],
        imports=["tester"], mock_targets=["tester"],
    )
    code = generate_mock_setup(analysis, mock_returns={
        "tester.send_cmd": {"default": {"status": 0, "data": "mock_data"}}
    })
    assert "mock" in code.lower() or "Mock" in code
    assert "tester" in code
    assert "send_cmd" in code


def test_generate_mock_with_custom_returns():
    analysis = AnalysisResult(
        file_path="test.py",
        functions=[FunctionInfo(
            name="foo", params=[],
            external_calls=[
                FunctionCall("hw", "read", ["0x00"], 1),
                FunctionCall("hw", "write", ["0x00", "data"], 2),
            ],
            branches=[], total_paths=1, return_types=["None"],
            random_variables=[],
        )],
        imports=["hw"], mock_targets=["hw"],
    )
    code = generate_mock_setup(analysis, mock_returns={
        "hw.read": {"default": {"value": 42}},
    })
    assert "create_hw_mock" in code
    assert "read" in code
    assert "write" in code


def test_no_mock_targets():
    analysis = AnalysisResult(
        file_path="test.py",
        functions=[], imports=[], mock_targets=[],
    )
    code = generate_mock_setup(analysis)
    assert "import pytest" in code
    # Should still be valid Python
    assert "MagicMock" in code
