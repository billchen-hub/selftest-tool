"""Multi-backend AI client for calling on-premise models."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("[selftest.ai_client]")


class AIProviderError(Exception):
    """Raised when AI provider call fails."""


class AIClient:
    """Call AI via OpenAI-compatible API or Nexus company platform.

    Providers:
      - "local_llm": OpenAI-compatible API (vLLM, Ollama, etc.)
      - "company_platform": Nexus REST API (http://ainexus.phison.com:5155)
    """

    def __init__(self, provider: str, config: dict):
        self.provider = provider
        self.config = config

    def generate(self, prompt: str, files: list[dict] | None = None) -> str:
        """Send prompt to AI and return response text.

        Args:
            prompt: the prompt text
            files: optional list of file dicts [{"fileId": int, "fileName": str}]
                   (only for company_platform with uploaded files)
        """
        if self.provider == "local_llm":
            return self._call_openai_compatible(prompt)
        elif self.provider == "company_platform":
            return self._call_nexus(prompt, files=files or [])
        else:
            raise AIProviderError(f"Unknown provider: {self.provider}")

    def upload_file(self, file_path: Path) -> int | None:
        """Upload a file to the Nexus platform and return its fileId.

        Only available for company_platform provider.
        Returns None on failure.
        """
        if self.provider != "company_platform":
            logger.warning("upload_file is only available for company_platform")
            return None

        import requests

        base_url = self.config.get("base_url", "http://ainexus.phison.com:5155")
        api_key = self.config.get("api_key", "")
        url = f"{base_url}/api/external/v1/Files/upload"
        timeout = int(self.config.get("timeout", 120))

        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                headers = {"X-API-Key": api_key}
                form_data = {"description": "selftest upload", "isPublic": "false"}
                response = requests.post(
                    url, data=form_data, files=files, headers=headers, timeout=timeout,
                )
                response.raise_for_status()
                data = response.json()
                return data["data"]["fileId"]
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return None

    # ---- OpenAI-compatible backend ----

    def _call_openai_compatible(self, prompt: str) -> str:
        """Call OpenAI-compatible API (local vLLM, Ollama, etc.)."""
        try:
            from openai import OpenAI
        except ImportError:
            raise AIProviderError(
                "openai 套件未安裝。如需使用 local_llm 後端，請執行: pip install selftest[local_llm]\n"
                "如果只用公司 AI 平台（Nexus），請在 selftest.ini 設定 provider = company_platform"
            )

        client = OpenAI(
            base_url=self.config.get("endpoint", "http://localhost:8080/v1"),
            api_key=self.config.get("api_key", "not-needed"),
        )

        timeout = float(self.config.get("timeout", 120))
        max_tokens = int(self.config.get("max_response_tokens", 4000))

        # Retry once on failure
        last_err = None
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=self.config.get("model", "qwen-72b"),
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.2,
                    timeout=timeout,
                )
                content = response.choices[0].message.content
                if content is None:
                    raise AIProviderError("AI returned empty response")
                return content
            except Exception as e:
                last_err = e
                if attempt == 0:
                    logger.warning(f"AI call failed (attempt 1), retrying: {e}")

        raise AIProviderError(f"AI call failed after 2 attempts: {last_err}")

    # ---- Nexus REST API backend ----

    def _call_nexus(self, prompt: str, files: list[dict] | None = None) -> str:
        """Call Nexus AI platform via REST API.

        API: POST /api/external/v1/callAgent/json
        Auth: X-API-Key header
        Payload: shareCode, prompt (wrapped in <<<>>>), previousMessage, files
        Response: response_data['content']
        """
        import requests

        base_url = self.config.get("base_url", "http://ainexus.phison.com:5155")
        api_key = self.config.get("api_key", "")
        share_code = self.config.get("share_code", "")
        timeout = int(self.config.get("timeout", 120))

        url = f"{base_url}/api/external/v1/callAgent/json"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        }

        # Build payload matching Nexus API format
        # System prompt as role 0, user prompt wrapped in <<<>>>
        system_msg = {
            "role": 0,
            "message": "You are a test generation assistant for Python firmware verification scripts.",
        }
        payload: dict[str, Any] = {
            "shareCode": share_code,
            "prompt": f"<<<{prompt}>>>",
            "previousMessage": [system_msg],
            "files": files or [],
        }

        # Retry once on failure
        last_err = None
        for attempt in range(2):
            try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=timeout,
                )
                response.raise_for_status()
                data = response.json()

                content = data.get("content")
                if not content:
                    raise AIProviderError(f"Nexus returned empty content: {data}")
                return content

            except requests.exceptions.Timeout:
                last_err = AIProviderError("Nexus API timeout")
                if attempt == 0:
                    logger.warning("Nexus call timed out, retrying")
            except requests.exceptions.RequestException as e:
                last_err = AIProviderError(f"Nexus API error: {e}")
                if attempt == 0:
                    logger.warning(f"Nexus call failed (attempt 1), retrying: {e}")
            except Exception as e:
                last_err = AIProviderError(f"Nexus call error: {e}")
                if attempt == 0:
                    logger.warning(f"Nexus call failed (attempt 1), retrying: {e}")

        raise last_err or AIProviderError("Nexus call failed")
