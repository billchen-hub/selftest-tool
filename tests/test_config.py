from pathlib import Path
from selftest.config import load_config


def test_load_config_from_ini(tmp_path):
    ini = tmp_path / "selftest.ini"
    ini.write_text("""
[general]
source_dirs = scripts/
lib_dirs = lib/
mock_modules = tester, hardware_interface
never_mock = lib.utils
coverage_threshold = 80

[ai]
provider = local_llm

[local_llm]
endpoint = http://localhost:8080/v1
model = qwen-72b
""", encoding="utf-8")
    config = load_config(ini)
    assert config.ai_provider == "local_llm"
    assert config.mock_modules == ["tester", "hardware_interface"]
    assert config.never_mock == ["lib.utils"]
    assert config.coverage_threshold == 80
    assert config.local_llm["endpoint"] == "http://localhost:8080/v1"
    assert config.local_llm["model"] == "qwen-72b"


def test_env_var_expansion(tmp_path, monkeypatch):
    monkeypatch.setenv("SELFTEST_API_KEY", "secret123")
    monkeypatch.setenv("SELFTEST_SHARE_CODE", "ABC")
    ini = tmp_path / "selftest.ini"
    ini.write_text("""
[ai]
provider = company_platform

[company_platform]
script_path = call_api.py
api_key = ${SELFTEST_API_KEY}
share_code = $SELFTEST_SHARE_CODE
""", encoding="utf-8")
    config = load_config(ini)
    assert config.ai_provider == "company_platform"
    assert config.company_platform["api_key"] == "secret123"
    assert config.company_platform["share_code"] == "ABC"


def test_missing_config_uses_defaults():
    config = load_config(Path("nonexistent_path_12345.ini"))
    assert config.ai_provider == "local_llm"
    assert config.coverage_threshold == 80
    assert config.mock_modules == ["tester"]


def test_token_limits(tmp_path):
    ini = tmp_path / "selftest.ini"
    ini.write_text("""
[ai]
provider = local_llm
max_prompt_tokens = 8000
max_response_tokens = 2000
""", encoding="utf-8")
    config = load_config(ini)
    assert config.max_prompt_tokens == 8000
    assert config.max_response_tokens == 2000
