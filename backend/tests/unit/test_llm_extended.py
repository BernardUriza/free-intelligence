"""
Extended unit tests for LLM provider module.
Tests utility functions and data structures that don't require API mocking.

Coverage targets: pad_embedding_to_768, sanitize_error_message, LLMProviderType, LLMResponse
"""

from __future__ import annotations

import numpy as np
import pytest
from backend.providers import (
    LLMProviderType,
    LLMResponse,
    pad_embedding_to_768,
    sanitize_error_message,
)


class TestPadEmbeddingTo768:
    """Tests for pad_embedding_to_768 function."""

    def test_pad_embedding_smaller_than_768(self):
        """Should zero-pad embeddings smaller than 768 dims."""
        emb_384 = np.random.rand(384).astype(np.float32)
        result = pad_embedding_to_768(emb_384)
        
        assert result.shape == (768,)
        # First 384 dims should match original
        np.testing.assert_array_equal(result[:384], emb_384)
        # Rest should be zeros
        np.testing.assert_array_equal(result[384:], np.zeros(384))

    def test_pad_embedding_exactly_768(self):
        """Should return unchanged if already 768 dims."""
        emb_768 = np.random.rand(768).astype(np.float32)
        result = pad_embedding_to_768(emb_768)
        
        assert result.shape == (768,)
        np.testing.assert_array_equal(result, emb_768)

    def test_pad_embedding_larger_than_768_truncates(self):
        """Should truncate embeddings larger than 768 dims."""
        emb_1024 = np.random.rand(1024).astype(np.float32)
        result = pad_embedding_to_768(emb_1024)
        
        assert result.shape == (768,)
        np.testing.assert_array_equal(result, emb_1024[:768])

    def test_pad_embedding_very_small(self):
        """Should handle very small embeddings."""
        emb_32 = np.random.rand(32).astype(np.float32)
        result = pad_embedding_to_768(emb_32)
        
        assert result.shape == (768,)
        np.testing.assert_array_equal(result[:32], emb_32)
        np.testing.assert_array_equal(result[32:], np.zeros(736))

    def test_pad_embedding_preserves_float32(self):
        """Result should be float32."""
        emb = np.random.rand(256).astype(np.float32)
        result = pad_embedding_to_768(emb)
        
        assert result.dtype == np.float32


class TestSanitizeErrorMessage:
    """Tests for sanitize_error_message function."""

    def test_sanitize_anthropic_api_key(self):
        """Should redact Anthropic API keys."""
        error = "API key sk-ant-api03-abc123DEF456_789 is invalid"
        result = sanitize_error_message(error)
        
        assert "[REDACTED_API_KEY]" in result
        assert "sk-ant-api03" not in result

    def test_sanitize_generic_api_key(self):
        """Should redact generic API keys."""
        error = 'api_key=abcdefghij1234567890klmnopqrstuv'
        result = sanitize_error_message(error)
        
        assert "[REDACTED]" in result.lower() or "api_key" in result

    def test_sanitize_bearer_token(self):
        """Should redact bearer tokens."""
        error = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 expired"
        result = sanitize_error_message(error)
        
        assert "[REDACTED_TOKEN]" in result
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    def test_sanitize_truncates_long_messages(self):
        """Should truncate messages longer than max_length."""
        long_error = "A" * 200
        result = sanitize_error_message(long_error, max_length=100)
        
        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")

    def test_sanitize_no_truncation_when_zero_max_length(self):
        """Should not truncate when max_length is 0."""
        long_error = "A" * 200
        result = sanitize_error_message(long_error, max_length=0)
        
        assert len(result) == 200

    def test_sanitize_short_message_unchanged(self):
        """Short messages without sensitive data should be unchanged."""
        error = "Connection refused"
        result = sanitize_error_message(error)
        
        assert result == error

    def test_sanitize_multiple_api_keys(self):
        """Should redact multiple API keys."""
        error = "Key1: sk-ant-api03-abc123 and Key2: sk-ant-api03-def456"
        result = sanitize_error_message(error, max_length=0)
        
        assert result.count("[REDACTED_API_KEY]") == 2

    def test_sanitize_case_insensitive_bearer(self):
        """Bearer token redaction should be case insensitive."""
        error = "BEARER abcdefghij1234567890klmnop invalid"
        result = sanitize_error_message(error, max_length=0)
        
        assert "[REDACTED_TOKEN]" in result


class TestLLMProviderType:
    """Tests for LLMProviderType enum."""

    def test_claude_provider_type(self):
        """Should have CLAUDE provider."""
        assert LLMProviderType.CLAUDE.value == "claude"

    def test_ollama_provider_type(self):
        """Should have OLLAMA provider."""
        assert LLMProviderType.OLLAMA.value == "ollama"

    def test_openai_provider_type(self):
        """Should have OPENAI provider."""
        assert LLMProviderType.OPENAI.value == "openai"

    def test_azure_provider_type(self):
        """Should have AZURE provider."""
        assert LLMProviderType.AZURE.value == "azure"

    def test_provider_type_from_string(self):
        """Should create enum from string value."""
        provider = LLMProviderType("claude")
        assert provider == LLMProviderType.CLAUDE

    def test_all_provider_types(self):
        """Should have exactly 4 providers."""
        providers = list(LLMProviderType)
        assert len(providers) == 4


class TestLLMResponse:
    """Tests for LLMResponse data class."""

    def test_llm_response_creation_minimal(self):
        """Should create response with required fields."""
        response = LLMResponse(
            content="Hello world",
            model="claude-3-5-sonnet",
            provider="claude",
            tokens_used=100,
        )
        
        assert response.content == "Hello world"
        assert response.model == "claude-3-5-sonnet"
        assert response.provider == "claude"
        assert response.tokens_used == 100
        assert response.cost_usd is None
        assert response.latency_ms is None
        assert response.metadata is None

    def test_llm_response_creation_full(self):
        """Should create response with all fields."""
        metadata = {"input_tokens": 50, "output_tokens": 50}
        response = LLMResponse(
            content="Generated text",
            model="qwen3:1.7b",
            provider="ollama",
            tokens_used=200,
            cost_usd=0.0001,
            latency_ms=150.5,
            metadata=metadata,
        )
        
        assert response.content == "Generated text"
        assert response.model == "qwen3:1.7b"
        assert response.provider == "ollama"
        assert response.tokens_used == 200
        assert response.cost_usd == 0.0001
        assert response.latency_ms == 150.5
        assert response.metadata == metadata

    def test_llm_response_empty_content(self):
        """Should handle empty content."""
        response = LLMResponse(
            content="",
            model="test",
            provider="test",
            tokens_used=0,
        )
        
        assert response.content == ""

    def test_llm_response_slots(self):
        """Should use __slots__ for memory efficiency."""
        assert hasattr(LLMResponse, "__slots__")
        assert "content" in LLMResponse.__slots__
        assert "model" in LLMResponse.__slots__
        assert "provider" in LLMResponse.__slots__

    def test_llm_response_zero_cost(self):
        """Should handle zero cost (local models)."""
        response = LLMResponse(
            content="Local response",
            model="qwen3:1.7b",
            provider="ollama",
            tokens_used=500,
            cost_usd=0.0,  # Local = free
        )
        
        assert response.cost_usd == 0.0

    def test_llm_response_high_latency(self):
        """Should handle high latency values."""
        response = LLMResponse(
            content="Slow response",
            model="test",
            provider="test",
            tokens_used=100,
            latency_ms=30000.0,  # 30 seconds
        )
        
        assert response.latency_ms == 30000.0

    def test_llm_response_complex_metadata(self):
        """Should handle complex metadata."""
        metadata = {
            "input_tokens": 100,
            "output_tokens": 200,
            "stop_reason": "end_turn",
            "model_version": "2024-10",
            "thinking": {"enabled": True, "tokens": 50},
        }
        response = LLMResponse(
            content="Response",
            model="claude",
            provider="claude",
            tokens_used=300,
            metadata=metadata,
        )
        
        assert response.metadata["thinking"]["enabled"] is True
        assert response.metadata["stop_reason"] == "end_turn"


class TestLLMModuleExports:
    """Tests that verify module exports work correctly."""

    def test_pad_embedding_is_importable(self):
        """pad_embedding_to_768 should be importable."""
        from backend.providers import pad_embedding_to_768
        assert callable(pad_embedding_to_768)

    def test_sanitize_error_is_importable(self):
        """sanitize_error_message should be importable."""
        from backend.providers import sanitize_error_message
        assert callable(sanitize_error_message)

    def test_llm_provider_type_is_importable(self):
        """LLMProviderType should be importable."""
        from backend.providers import LLMProviderType
        assert LLMProviderType.CLAUDE.value == "claude"

    def test_llm_response_is_importable(self):
        """LLMResponse should be importable."""
        from backend.providers import LLMResponse
        assert LLMResponse is not None
