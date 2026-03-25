"""INI config loader with environment variable expansion."""

from __future__ import annotations

import configparser
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


def _expand_env_vars(value: str) -> str:
    """Expand ${VAR} and $VAR references in a string."""
    return re.sub(
        r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)',
        lambda m: os.environ.get(m.group(1) or m.group(2), ''),
        value,
    )


def _split_list(value: str) -> list[str]:
    """Split comma-separated string into trimmed list, filtering empty."""
    return [v.strip() for v in value.split(',') if v.strip()]


@dataclass
class SelftestConfig:
    # [general]
    source_dirs: list[str] = field(default_factory=lambda: ["scripts/"])
    lib_dirs: list[str] = field(default_factory=lambda: ["lib/"])
    mock_modules: list[str] = field(default_factory=lambda: ["tester"])
    never_mock: list[str] = field(default_factory=list)
    coverage_threshold: int = 80

    # [ai]
    ai_provider: str = "local_llm"

    # [company_platform]
    company_platform: dict[str, str] = field(default_factory=dict)

    # [local_llm]
    local_llm: dict[str, str] = field(default_factory=dict)

    # [ai] token limits
    max_prompt_tokens: int = 4000
    max_response_tokens: int = 4000

    # [report]
    html_dir: str = ".selftest/reports/"
    keep_days: int = 30

    # Resolved selftest dir
    selftest_dir: str = ".selftest"


def load_config(ini_path: Path) -> SelftestConfig:
    """Load config from INI file. Missing file → defaults."""
    config = SelftestConfig()

    if not ini_path.exists():
        return config

    parser = configparser.ConfigParser()
    parser.read(str(ini_path), encoding="utf-8")

    # [general]
    if parser.has_section("general"):
        g = parser["general"]
        if "source_dirs" in g:
            config.source_dirs = _split_list(g["source_dirs"])
        if "lib_dirs" in g:
            config.lib_dirs = _split_list(g["lib_dirs"])
        if "mock_modules" in g:
            config.mock_modules = _split_list(g["mock_modules"])
        if "never_mock" in g:
            config.never_mock = _split_list(g["never_mock"])
        if "coverage_threshold" in g:
            config.coverage_threshold = int(g["coverage_threshold"])

    # [ai]
    if parser.has_section("ai"):
        ai = parser["ai"]
        config.ai_provider = ai.get("provider", "local_llm")
        if "max_prompt_tokens" in ai:
            config.max_prompt_tokens = int(ai["max_prompt_tokens"])
        if "max_response_tokens" in ai:
            config.max_response_tokens = int(ai["max_response_tokens"])

    # [company_platform]
    if parser.has_section("company_platform"):
        config.company_platform = {
            k: _expand_env_vars(v) for k, v in parser["company_platform"].items()
        }

    # [local_llm]
    if parser.has_section("local_llm"):
        config.local_llm = {
            k: _expand_env_vars(v) for k, v in parser["local_llm"].items()
        }

    # [report]
    if parser.has_section("report"):
        r = parser["report"]
        if "html_dir" in r:
            config.html_dir = r["html_dir"]
        if "keep_days" in r:
            config.keep_days = int(r["keep_days"])

    return config
