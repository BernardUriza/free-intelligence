"""
Free Intelligence - LLM Endpoint Tests

Tests for /llm/generate endpoint with cache validation.

File: tests/test_llm_endpoint.py
Created: 2025-10-29
Card: FI-CORE-FEAT-001
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from backend.llm_middleware import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_ollama_success():
    """Mock successful Ollama response."""
    with patch("backend.providers.ollama.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "Test response from Ollama",
            "done": True,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        yield mock_post


def test_generate_endpoint_success(client, mock_ollama_success) -> None:
    """Test /llm/generate returns 200 OK with valid payload."""
    payload = {
        "provider": "ollama",
        "model": "qwen2:7b",
        "prompt": "Hello world",
        "system": "",
        "params": {"temperature": 0.2, "max_tokens": 512},
        "stream": False,
    }

    response = client.post("/llm/generate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["text"] == "Test response from Ollama"
    assert "usage" in data
    assert "latency_ms" in data
    assert data["provider"] == "ollama"
    assert data["model"] == "qwen2:7b"
    assert "prompt_hash" in data
    assert data["cache_hit"] is False


def test_generate_endpoint_invalid_provider(client) -> None:
    """Test /llm/generate returns 400 for invalid provider."""
    payload = {
        "provider": "invalid_provider",
        "model": "test",
        "prompt": "Hello",
        "stream": False,
    }

    response = client.post("/llm/generate", json=payload)

    assert response.status_code == 422  # Pydantic validation error


def test_generate_endpoint_stream_not_supported(client) -> None:
    """Test /llm/generate returns 422 when stream=true."""
    payload = {
        "provider": "ollama",
        "model": "qwen2:7b",
        "prompt": "Hello",
        "stream": True,
    }

    response = client.post("/llm/generate", json=payload)

    assert response.status_code == 422  # Pydantic validation error


def test_generate_endpoint_cache_hit(client, mock_ollama_success) -> None:
    """Test /llm/generate returns cache_hit=true on 2nd call."""
    payload = {
        "provider": "ollama",
        "model": "qwen2:7b",
        "prompt": "Cache test prompt",
        "system": "",
        "params": {"temperature": 0.2, "max_tokens": 512},
        "stream": False,
    }

    # First call (miss)
    response1 = client.post("/llm/generate", json=payload)
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["cache_hit"] is False

    # Second call (hit)
    response2 = client.post("/llm/generate", json=payload)
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["cache_hit"] is True
    assert data2["latency_ms"] == 0  # Cache hit should be ~0ms
    assert data2["text"] == data1["text"]


def test_generate_endpoint_missing_prompt(client) -> None:
    """Test /llm/generate returns 422 for missing prompt."""
    payload = {
        "provider": "ollama",
        "model": "qwen2:7b",
        "stream": False,
    }

    response = client.post("/llm/generate", json=payload)

    assert response.status_code == 422


def test_health_endpoint(client) -> None:
    """Test /health endpoint returns status."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "llm_adapters" in data
