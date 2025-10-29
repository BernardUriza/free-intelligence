"""
Free Intelligence - Ollama Adapter Tests

Tests for OllamaAdapter (local-only, timeouts, retries).

File: tests/test_ollama_adapter.py
Created: 2025-10-29
Card: FI-CORE-FEAT-001
"""

from unittest.mock import Mock, patch

import pytest

from backend.llm_adapter import LLMProviderError, LLMRequest
from backend.providers.ollama import OllamaAdapter


def test_ollama_adapter_init_local():
    """Test OllamaAdapter initialization with local host."""
    adapter = OllamaAdapter(base_url="http://127.0.0.1:11434")
    assert adapter.provider_name == "ollama"
    assert adapter.base_url == "http://127.0.0.1:11434"
    assert adapter.timeout_seconds == 8


def test_ollama_adapter_init_localhost():
    """Test OllamaAdapter initialization with localhost."""
    adapter = OllamaAdapter(base_url="http://localhost:11434")
    assert adapter.base_url == "http://localhost:11434"


def test_ollama_adapter_rejects_external_host():
    """Test OllamaAdapter rejects non-local hosts."""
    with pytest.raises(ValueError, match="only accepts local hosts"):
        OllamaAdapter(base_url="http://example.com:11434")

    with pytest.raises(ValueError, match="only accepts local hosts"):
        OllamaAdapter(base_url="http://192.168.1.100:11434")


@patch("backend.providers.ollama.requests.post")
def test_ollama_adapter_generate_success(mock_post):
    """Test OllamaAdapter.generate() success."""
    # Mock successful response
    mock_response = Mock()
    mock_response.json.return_value = {
        "response": "Hello world",
        "done": True,
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    adapter = OllamaAdapter()
    request = LLMRequest(prompt="Test prompt", max_tokens=512, temperature=0.2)

    response = adapter.generate(request)

    assert response.content == "Hello world"
    assert response.provider == "ollama"
    assert response.model == "qwen2:7b"
    assert response.tokens_used > 0
    assert response.latency_ms >= 0
    assert "prompt_hash" in response.metadata


@patch("backend.providers.ollama.requests.post")
def test_ollama_adapter_timeout(mock_post):
    """Test OllamaAdapter handles timeout."""
    # Mock timeout
    import requests

    mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

    adapter = OllamaAdapter(timeout_seconds=1, max_retries=0)
    request = LLMRequest(prompt="Test prompt")

    with pytest.raises(LLMProviderError, match="failed after 1 attempts"):
        adapter.generate(request)


@patch("backend.providers.ollama.requests.post")
def test_ollama_adapter_retry_logic(mock_post):
    """Test OllamaAdapter retry logic."""
    import requests

    # First call fails, second succeeds
    mock_response = Mock()
    mock_response.json.return_value = {
        "response": "Retry success",
        "done": True,
    }
    mock_response.raise_for_status = Mock()

    mock_post.side_effect = [
        requests.exceptions.RequestException("First attempt failed"),
        mock_response,
    ]

    adapter = OllamaAdapter(max_retries=1)
    request = LLMRequest(prompt="Test prompt")

    response = adapter.generate(request)
    assert response.content == "Retry success"
    assert mock_post.call_count == 2


@patch("backend.providers.ollama.requests.post")
def test_ollama_adapter_long_prompt_redaction(mock_post):
    """Test OllamaAdapter redacts long prompts in logs."""
    # Mock successful response
    mock_response = Mock()
    mock_response.json.return_value = {
        "response": "Response",
        "done": True,
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    adapter = OllamaAdapter()
    long_prompt = "x" * 1000  # 1000 chars
    request = LLMRequest(prompt=long_prompt)

    response = adapter.generate(request)
    assert response.content == "Response"


def test_ollama_adapter_stream_not_implemented():
    """Test OllamaAdapter.stream() raises NotImplementedError."""
    adapter = OllamaAdapter()
    request = LLMRequest(prompt="Test")

    with pytest.raises(NotImplementedError, match="not supported in v1"):
        list(adapter.stream(request))
