from unittest.mock import patch, MagicMock
from selftest.generator.ai_client import AIClient, AIProviderError
import pytest


def test_local_llm_call():
    client = AIClient(provider="local_llm", config={
        "endpoint": "http://localhost:8080/v1",
        "model": "qwen-72b",
        "api_key": "",
    })
    with patch.object(client, '_call_openai_compatible') as mock_call:
        mock_call.return_value = "```python\ndef test_foo(): pass\n```"
        result = client.generate("test prompt")
        assert "test_foo" in result
        mock_call.assert_called_once_with("test prompt")


def test_nexus_api_call():
    """Test Nexus REST API call."""
    client = AIClient(provider="company_platform", config={
        "base_url": "http://ainexus.phison.com:5155",
        "api_key": "test-key",
        "share_code": "test-code",
    })
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"content": "generated test code"}
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response) as mock_post:
        result = client.generate("test prompt")
        assert result == "generated test code"

        # Verify correct API call
        call_args = mock_post.call_args
        assert "callAgent/json" in call_args[0][0]
        assert call_args[1]["headers"]["X-API-Key"] == "test-key"
        payload = call_args[1]["json"]
        assert payload["shareCode"] == "test-code"
        assert "<<<test prompt>>>" == payload["prompt"]


def test_nexus_with_files():
    """Test Nexus API call with file attachments."""
    client = AIClient(provider="company_platform", config={
        "base_url": "http://test:5155",
        "api_key": "key",
        "share_code": "code",
    })
    mock_response = MagicMock()
    mock_response.json.return_value = {"content": "response with file context"}
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response):
        files = [{"fileId": 123, "fileName": "spec.pdf"}]
        result = client.generate("analyze this", files=files)
        assert result == "response with file context"


def test_nexus_timeout_retry():
    """Test retry on timeout."""
    import requests
    client = AIClient(provider="company_platform", config={
        "base_url": "http://test:5155",
        "api_key": "key",
        "share_code": "code",
        "timeout": "5",
    })
    mock_success = MagicMock()
    mock_success.json.return_value = {"content": "ok"}
    mock_success.raise_for_status = MagicMock()

    with patch("requests.post", side_effect=[
        requests.exceptions.Timeout("timed out"),
        mock_success,
    ]):
        result = client.generate("prompt")
        assert result == "ok"


def test_nexus_failure_after_retry():
    """Test failure after 2 attempts."""
    import requests
    client = AIClient(provider="company_platform", config={
        "base_url": "http://test:5155",
        "api_key": "key",
        "share_code": "code",
        "timeout": "5",
    })
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("refused")):
        with pytest.raises(AIProviderError, match="Nexus"):
            client.generate("prompt")


def test_upload_file(tmp_path):
    """Test file upload to Nexus."""
    client = AIClient(provider="company_platform", config={
        "base_url": "http://test:5155",
        "api_key": "key",
    })
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')")

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"fileId": 42}}
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response):
        file_id = client.upload_file(test_file)
        assert file_id == 42


def test_upload_file_wrong_provider():
    """Upload only works for company_platform."""
    client = AIClient(provider="local_llm", config={})
    result = client.upload_file(Path("test.py"))
    assert result is None


def test_unknown_provider():
    client = AIClient(provider="unknown", config={})
    with pytest.raises(AIProviderError, match="Unknown provider"):
        client.generate("prompt")


def test_local_llm_retry():
    """Test OpenAI-compatible retry logic."""
    client = AIClient(provider="local_llm", config={
        "endpoint": "http://localhost:8080/v1",
        "model": "test",
        "api_key": "",
    })
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="result"))]

    with patch("openai.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            ConnectionError("first fail"),
            mock_response,
        ]
        result = client._call_openai_compatible("prompt")
        assert result == "result"
        assert mock_client.chat.completions.create.call_count == 2


from pathlib import Path
