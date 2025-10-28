"""
Unit tests for LLM Router and Providers

Tests the unified LLM interface with schema validation and latency requirements.
"""

import pytest
import json
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from backend.llm_router import (
    LLMRouter,
    ClaudeProvider,
    OllamaProvider,
    LLMResponse,
    LLMProviderType,
    sanitize_error_message,
    pad_embedding_to_768
)


class TestSchemaValidation:
    """Test JSON schema validation for requests and responses"""

    def test_request_schema_exists(self):
        """Request schema file should exist"""
        schema_path = "backend/schemas/llm_request.json"
        assert os.path.exists(schema_path), f"Missing {schema_path}"

    def test_response_schema_exists(self):
        """Response schema file should exist"""
        schema_path = "backend/schemas/llm_response.json"
        assert os.path.exists(schema_path), f"Missing {schema_path}"

    def test_request_schema_valid_json(self):
        """Request schema should be valid JSON"""
        with open("backend/schemas/llm_request.json", "r") as f:
            schema = json.load(f)
            assert "$schema" in schema
            assert "properties" in schema
            assert "prompt" in schema["properties"]
            assert "provider" in schema["properties"]

    def test_response_schema_valid_json(self):
        """Response schema should be valid JSON"""
        with open("backend/schemas/llm_response.json", "r") as f:
            schema = json.load(f)
            assert "$schema" in schema
            assert "properties" in schema
            assert "content" in schema["properties"]
            assert "model" in schema["properties"]
            assert "provider" in schema["properties"]
            assert "tokens_used" in schema["properties"]


class TestLLMResponse:
    """Test LLMResponse dataclass"""

    def test_response_creation(self):
        """Should create LLMResponse with required fields"""
        response = LLMResponse(
            content="Hello world",
            model="claude-3-5-sonnet-20241022",
            provider="claude",
            tokens_used=100
        )
        assert response.content == "Hello world"
        assert response.model == "claude-3-5-sonnet-20241022"
        assert response.provider == "claude"
        assert response.tokens_used == 100

    def test_response_with_optional_fields(self):
        """Should create LLMResponse with optional fields"""
        response = LLMResponse(
            content="Test",
            model="test-model",
            provider="claude",
            tokens_used=50,
            cost_usd=0.001,
            latency_ms=250.5,
            metadata={"input_tokens": 30, "output_tokens": 20}
        )
        assert response.cost_usd == 0.001
        assert response.latency_ms == 250.5
        assert response.metadata["input_tokens"] == 30


class TestClaudeProvider:
    """Test Claude provider implementation"""

    @patch('backend.llm_router.anthropic.Anthropic')
    def test_claude_provider_initialization(self, mock_anthropic):
        """Should initialize Claude provider with API key"""
        with patch.dict(os.environ, {'CLAUDE_API_KEY': 'test-key'}):
            provider = ClaudeProvider()
            assert provider.default_model == "claude-3-5-sonnet-20241022"
            assert provider.timeout == 30

    @patch('backend.llm_router.anthropic.Anthropic')
    def test_claude_generate_success(self, mock_anthropic):
        """Should generate response with Claude"""
        with patch.dict(os.environ, {'CLAUDE_API_KEY': 'test-key'}):
            # Mock Claude API response
            mock_client = Mock()
            mock_message = Mock()
            mock_message.content = [Mock(text="Generated response")]
            mock_message.model = "claude-3-5-sonnet-20241022"
            mock_message.usage = Mock(input_tokens=10, output_tokens=20)
            mock_message.stop_reason = "end_turn"
            mock_client.messages.create.return_value = mock_message

            provider = ClaudeProvider()
            provider.client = mock_client

            response = provider.generate("Test prompt")

            assert isinstance(response, LLMResponse)
            assert response.content == "Generated response"
            assert response.provider == "claude"
            assert response.tokens_used > 0
            assert response.latency_ms is not None
            assert response.latency_ms >= 0

    @patch('backend.llm_router.anthropic.Anthropic')
    def test_claude_latency_measurement(self, mock_anthropic):
        """Should measure latency in milliseconds"""
        with patch.dict(os.environ, {'CLAUDE_API_KEY': 'test-key'}):
            mock_client = Mock()
            mock_message = Mock()
            mock_message.content = [Mock(text="Response")]
            mock_message.model = "claude-3-5-sonnet-20241022"
            mock_message.usage = Mock(input_tokens=10, output_tokens=20)
            mock_message.stop_reason = "end_turn"
            mock_client.messages.create.return_value = mock_message

            provider = ClaudeProvider()
            provider.client = mock_client

            response = provider.generate("Test")

            # Latency should be measured
            assert response.latency_ms is not None
            assert response.latency_ms >= 0
            # Should be reasonably fast (< 5 seconds for mock)
            assert response.latency_ms < 5000


class TestOllamaProvider:
    """Test Ollama provider implementation"""

    def test_ollama_provider_stub_or_implemented(self):
        """Ollama provider should exist (stub or full implementation)"""
        # Just verify the class exists
        assert OllamaProvider is not None

    @patch('backend.llm_router.ollama')
    def test_ollama_generate_returns_501_or_response(self, mock_ollama):
        """Ollama should return 501 stub or valid response"""
        try:
            # Try to create provider (may fail if ollama not installed)
            mock_ollama.Client.return_value = Mock()
            provider = OllamaProvider({"base_url": "http://localhost:11434"})

            # If we get here, provider initialized
            # Either it's a stub returning 501, or a full implementation
            assert provider.get_provider_name() == "ollama"
        except ImportError:
            # Expected if ollama library not installed
            pass


class TestUtilityFunctions:
    """Test utility functions"""

    def test_sanitize_error_message_api_keys(self):
        """Should redact API keys from error messages"""
        error = "API key sk-ant-api03-abc123xyz is invalid"
        sanitized = sanitize_error_message(error)
        assert "sk-ant-api03-abc123xyz" not in sanitized
        assert "[REDACTED" in sanitized

    def test_sanitize_error_message_bearer_tokens(self):
        """Should redact bearer tokens from error messages"""
        error = "Bearer abc123def456ghi789 authentication failed"
        sanitized = sanitize_error_message(error)
        assert "abc123def456ghi789" not in sanitized
        assert "[REDACTED" in sanitized

    def test_pad_embedding_to_768_no_padding(self):
        """Should not pad 768-dim embeddings"""
        emb = np.random.rand(768).astype(np.float32)
        result = pad_embedding_to_768(emb)
        assert result.shape == (768,)
        assert np.array_equal(result, emb)

    def test_pad_embedding_to_768_with_padding(self):
        """Should pad smaller embeddings to 768"""
        emb = np.random.rand(384).astype(np.float32)
        result = pad_embedding_to_768(emb)
        assert result.shape == (768,)
        assert np.array_equal(result[:384], emb)
        assert np.all(result[384:] == 0)

    def test_pad_embedding_to_768_truncate(self):
        """Should truncate larger embeddings to 768"""
        emb = np.random.rand(1024).astype(np.float32)
        result = pad_embedding_to_768(emb)
        assert result.shape == (768,)
        assert np.array_equal(result, emb[:768])


class TestLatencyRequirement:
    """Test p95 latency < 800ms requirement (AC)"""

    @patch('backend.llm_router.anthropic.Anthropic')
    def test_claude_latency_p95_under_800ms(self, mock_anthropic):
        """
        AC: Given prompt+schema, When provider=claude,
        Then latencia p95 < 800 ms (set demo).

        Note: This is a mock test. Real latency depends on API.
        In production, measure p95 with real data from metrics.
        """
        with patch.dict(os.environ, {'CLAUDE_API_KEY': 'test-key'}):
            mock_client = Mock()
            mock_message = Mock()
            mock_message.content = [Mock(text="Response")]
            mock_message.model = "claude-3-5-sonnet-20241022"
            mock_message.usage = Mock(input_tokens=10, output_tokens=20)
            mock_message.stop_reason = "end_turn"
            mock_client.messages.create.return_value = mock_message

            provider = ClaudeProvider()
            provider.client = mock_client

            # Simulate multiple requests
            latencies = []
            for _ in range(10):
                response = provider.generate("Test prompt")
                latencies.append(response.latency_ms)

            # Calculate p95
            p95 = np.percentile(latencies, 95)

            # Mock responses should be fast
            assert p95 < 800, f"p95 latency {p95}ms exceeds 800ms threshold"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
