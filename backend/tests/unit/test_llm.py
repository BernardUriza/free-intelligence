"""
Unit tests for backend/providers/llm.py

Tests cover:
- Utility functions (pad_embedding_to_768, sanitize_error_message)
- LLMProviderType enum
- LLMResponse dataclass
- get_provider factory function
- Provider initialization (with mocks)

Following HIPAA: No PHI in tests, mock all external API calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from backend.providers.llm import (
    LLMProvider,
    LLMProviderType,
    LLMResponse,
    get_provider,
    pad_embedding_to_768,
    sanitize_error_message,
)


# ==============================================================================
# Tests for pad_embedding_to_768()
# ==============================================================================
class TestPadEmbeddingTo768:
    """Tests for the pad_embedding_to_768 utility function."""

    def test_already_768_dimensions(self) -> None:
        """Embedding with 768 dimensions should be returned unchanged."""
        embedding = np.random.rand(768).astype(np.float32)
        result = pad_embedding_to_768(embedding)

        assert result.shape == (768,)
        np.testing.assert_array_equal(result, embedding)

    def test_smaller_embedding_padded(self) -> None:
        """Embedding smaller than 768 should be zero-padded."""
        embedding = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        result = pad_embedding_to_768(embedding)

        assert result.shape == (768,)
        # First 3 elements should match
        np.testing.assert_array_equal(result[:3], embedding)
        # Rest should be zeros
        np.testing.assert_array_equal(result[3:], np.zeros(765, dtype=np.float32))

    def test_384_dimensional_embedding(self) -> None:
        """Common case: 384-dim embedding padded to 768."""
        embedding = np.random.rand(384).astype(np.float32)
        result = pad_embedding_to_768(embedding)

        assert result.shape == (768,)
        np.testing.assert_array_equal(result[:384], embedding)
        np.testing.assert_array_equal(result[384:], np.zeros(384, dtype=np.float32))

    def test_larger_embedding_truncated(self) -> None:
        """Embedding larger than 768 should be truncated."""
        embedding = np.random.rand(1024).astype(np.float32)
        result = pad_embedding_to_768(embedding)

        assert result.shape == (768,)
        np.testing.assert_array_equal(result, embedding[:768])

    def test_empty_embedding(self) -> None:
        """Empty embedding should result in all zeros."""
        embedding = np.array([], dtype=np.float32)
        result = pad_embedding_to_768(embedding)

        assert result.shape == (768,)
        np.testing.assert_array_equal(result, np.zeros(768, dtype=np.float32))

    def test_single_element_embedding(self) -> None:
        """Single element embedding should be padded correctly."""
        embedding = np.array([42.0], dtype=np.float32)
        result = pad_embedding_to_768(embedding)

        assert result.shape == (768,)
        assert result[0] == 42.0
        np.testing.assert_array_equal(result[1:], np.zeros(767, dtype=np.float32))

    def test_output_dtype_is_float32(self) -> None:
        """Output should always be float32."""
        embedding = np.array([1.0, 2.0], dtype=np.float64)
        result = pad_embedding_to_768(embedding)

        assert result.dtype == np.float32


# ==============================================================================
# Tests for sanitize_error_message()
# ==============================================================================
class TestSanitizeErrorMessage:
    """Tests for the sanitize_error_message security function."""

    def test_anthropic_api_key_redacted(self) -> None:
        """Anthropic API keys (sk-ant-api*) should be redacted."""
        msg = "API key sk-ant-api03-abc123XYZ is invalid"
        result = sanitize_error_message(msg)

        assert "sk-ant-api" not in result
        assert "[REDACTED_API_KEY]" in result

    def test_generic_api_key_redacted(self) -> None:
        """Generic api_key patterns should be redacted."""
        msg = "Error: api_key=abcdefghij1234567890abcd is wrong"
        result = sanitize_error_message(msg, max_length=0)

        assert "abcdefghij" not in result
        assert "api_key=[REDACTED]" in result

    def test_bearer_token_redacted(self) -> None:
        """Bearer tokens should be redacted."""
        msg = "Auth failed: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = sanitize_error_message(msg, max_length=0)

        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "Bearer [REDACTED_TOKEN]" in result

    def test_message_truncation(self) -> None:
        """Long messages should be truncated."""
        msg = "A" * 200
        result = sanitize_error_message(msg, max_length=100)

        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")

    def test_no_truncation_when_max_length_zero(self) -> None:
        """max_length=0 should disable truncation."""
        msg = "A" * 200
        result = sanitize_error_message(msg, max_length=0)

        assert len(result) == 200

    def test_clean_message_unchanged(self) -> None:
        """Messages without sensitive data should remain unchanged."""
        msg = "Connection timeout after 30s"
        result = sanitize_error_message(msg)

        assert result == msg

    def test_multiple_sensitive_patterns(self) -> None:
        """Multiple sensitive patterns should all be redacted."""
        msg = "Key sk-ant-api03-test123 failed. Bearer abc123def456ghi789jkl0 also bad."
        result = sanitize_error_message(msg, max_length=0)

        assert "sk-ant-api" not in result
        assert "abc123def456ghi789jkl0" not in result

    def test_case_insensitive_api_key(self) -> None:
        """API key pattern should be case insensitive."""
        msg = "Error: API_KEY=secret1234567890abcdefgh"
        result = sanitize_error_message(msg, max_length=0)

        assert "secret123" not in result


# ==============================================================================
# Tests for LLMProviderType enum
# ==============================================================================
class TestLLMProviderType:
    """Tests for the LLMProviderType enumeration."""

    def test_claude_value(self) -> None:
        """CLAUDE enum should have value 'claude'."""
        assert LLMProviderType.CLAUDE.value == "claude"

    def test_ollama_value(self) -> None:
        """OLLAMA enum should have value 'ollama'."""
        assert LLMProviderType.OLLAMA.value == "ollama"

    def test_openai_value(self) -> None:
        """OPENAI enum should have value 'openai'."""
        assert LLMProviderType.OPENAI.value == "openai"

    def test_azure_value(self) -> None:
        """AZURE enum should have value 'azure'."""
        assert LLMProviderType.AZURE.value == "azure"

    def test_all_providers_unique(self) -> None:
        """All provider values should be unique."""
        values = [p.value for p in LLMProviderType]
        assert len(values) == len(set(values))

    def test_enum_membership(self) -> None:
        """Provider names should be valid enum members."""
        assert LLMProviderType("claude") == LLMProviderType.CLAUDE
        assert LLMProviderType("ollama") == LLMProviderType.OLLAMA

    def test_invalid_provider_raises(self) -> None:
        """Invalid provider name should raise ValueError."""
        with pytest.raises(ValueError):
            LLMProviderType("invalid_provider")


# ==============================================================================
# Tests for LLMResponse
# ==============================================================================
class TestLLMResponse:
    """Tests for the LLMResponse class."""

    def test_basic_creation(self) -> None:
        """LLMResponse should store all required fields."""
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

    def test_optional_fields_default_none(self) -> None:
        """Optional fields should default to None."""
        response = LLMResponse(
            content="test",
            model="test-model",
            provider="test",
            tokens_used=10,
        )

        assert response.cost_usd is None
        assert response.latency_ms is None
        assert response.metadata is None

    def test_all_fields(self) -> None:
        """LLMResponse should accept all optional fields."""
        metadata = {"reasoning_tokens": 500}
        response = LLMResponse(
            content="Full response",
            model="claude-3-5-sonnet",
            provider="claude",
            tokens_used=1000,
            cost_usd=0.05,
            latency_ms=1500.5,
            metadata=metadata,
        )

        assert response.cost_usd == 0.05
        assert response.latency_ms == 1500.5
        assert response.metadata == metadata

    def test_empty_content(self) -> None:
        """LLMResponse should accept empty content."""
        response = LLMResponse(
            content="",
            model="model",
            provider="provider",
            tokens_used=0,
        )

        assert response.content == ""

    def test_uses_slots(self) -> None:
        """LLMResponse should use __slots__ for memory efficiency."""
        assert hasattr(LLMResponse, "__slots__")
        assert "content" in LLMResponse.__slots__


# ==============================================================================
# Tests for get_provider factory
# ==============================================================================
class TestGetProvider:
    """Tests for the get_provider factory function."""

    def test_unknown_provider_raises_valueerror(self) -> None:
        """Unknown provider should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_provider("invalid_provider")

        assert "Unknown provider" in str(exc_info.value)
        assert "invalid_provider" in str(exc_info.value)

    def test_supported_providers_in_error_message(self) -> None:
        """Error message should list supported providers."""
        with pytest.raises(ValueError) as exc_info:
            get_provider("fake")

        error_msg = str(exc_info.value)
        assert "claude" in error_msg
        assert "ollama" in error_msg
        assert "azure" in error_msg

    def test_case_insensitive_provider_name(self) -> None:
        """Provider name should be case insensitive."""
        with patch.dict("os.environ", {"CLAUDE_API_KEY": "test-key"}):
            with patch("backend.providers.llm.anthropic.Anthropic"):
                provider = get_provider("CLAUDE")
                assert provider is not None
                assert provider.get_provider_name() == "claude"

    @patch.dict("os.environ", {"CLAUDE_API_KEY": "test-key"})
    @patch("backend.providers.llm.anthropic.Anthropic")
    def test_claude_provider_creation(self, mock_anthropic: MagicMock) -> None:
        """Factory should create ClaudeProvider for 'claude'."""
        provider = get_provider("claude")

        assert provider.get_provider_name() == "claude"
        mock_anthropic.assert_called_once()

    @patch("backend.providers.llm.ollama")
    def test_ollama_provider_creation(self, mock_ollama: MagicMock) -> None:
        """Factory should create OllamaProvider for 'ollama'."""
        mock_ollama.Client.return_value = MagicMock()

        provider = get_provider("ollama", {"base_url": "http://localhost:11434"})

        assert provider.get_provider_name() == "ollama"

    @patch.dict(
        "os.environ",
        {
            "AZURE_OPENAI_KEY": "test-key",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        },
    )
    @patch("backend.providers.llm.aiohttp")
    def test_azure_provider_creation(self, mock_aiohttp: MagicMock) -> None:
        """Factory should create AzureOpenAIProvider for 'azure'."""
        provider = get_provider("azure")

        assert provider.get_provider_name() == "azure"


# ==============================================================================
# Tests for ClaudeProvider initialization
# ==============================================================================
class TestClaudeProviderInit:
    """Tests for ClaudeProvider initialization."""

    def test_missing_api_key_raises(self) -> None:
        """Missing CLAUDE_API_KEY should raise ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            # Remove the key if it exists
            import os

            os.environ.pop("CLAUDE_API_KEY", None)

            with pytest.raises(ValueError) as exc_info:
                get_provider("claude")

            assert "CLAUDE_API_KEY" in str(exc_info.value)

    @patch.dict("os.environ", {"CLAUDE_API_KEY": "sk-test-key"})
    @patch("backend.providers.llm.anthropic.Anthropic")
    def test_default_model(self, mock_anthropic: MagicMock) -> None:
        """ClaudeProvider should use default model if not specified."""
        provider = get_provider("claude")

        assert provider.default_model == "claude-3-5-sonnet-20241022"

    @patch.dict("os.environ", {"CLAUDE_API_KEY": "sk-test-key"})
    @patch("backend.providers.llm.anthropic.Anthropic")
    def test_custom_model(self, mock_anthropic: MagicMock) -> None:
        """ClaudeProvider should use custom model from config."""
        provider = get_provider("claude", {"model": "claude-3-5-haiku-20241022"})

        assert provider.default_model == "claude-3-5-haiku-20241022"

    @patch.dict("os.environ", {"CLAUDE_API_KEY": "sk-test-key"})
    @patch("backend.providers.llm.anthropic.Anthropic")
    def test_custom_timeout(self, mock_anthropic: MagicMock) -> None:
        """ClaudeProvider should use custom timeout from config."""
        provider = get_provider("claude", {"timeout_seconds": 60})

        assert provider.timeout == 60


# ==============================================================================
# Tests for OllamaProvider initialization
# ==============================================================================
class TestOllamaProviderInit:
    """Tests for OllamaProvider initialization."""

    @patch("backend.providers.llm.ollama")
    def test_default_base_url(self, mock_ollama: MagicMock) -> None:
        """OllamaProvider should use hosts from configuration."""
        mock_ollama.Client.return_value = MagicMock()

        provider = get_provider("ollama")

        # base_url should be set from the first host
        assert provider.base_url is not None

    @patch("backend.providers.llm.ollama")
    def test_default_model(self, mock_ollama: MagicMock) -> None:
        """OllamaProvider should use default model if not specified."""
        mock_ollama.Client.return_value = MagicMock()

        provider = get_provider("ollama")

        # Default model is qwen3:1.7b
        assert provider.default_model == "qwen3:1.7b"

    @patch("backend.providers.llm.ollama")
    def test_custom_model(self, mock_ollama: MagicMock) -> None:
        """OllamaProvider should use custom model from config."""
        mock_ollama.Client.return_value = MagicMock()

        provider = get_provider("ollama", {"model": "llama3.2:1b"})

        assert provider.default_model == "llama3.2:1b"

    @patch("backend.providers.llm.ollama")
    def test_creates_client_per_host(self, mock_ollama: MagicMock) -> None:
        """OllamaProvider should create a client for each configured host."""
        mock_ollama.Client.return_value = MagicMock()

        provider = get_provider("ollama")

        # Should have at least one client
        assert len(provider.clients) >= 1


# ==============================================================================
# Tests for AzureOpenAIProvider initialization
# ==============================================================================
class TestAzureOpenAIProviderInit:
    """Tests for AzureOpenAIProvider initialization."""

    def test_missing_endpoint_raises(self) -> None:
        """Missing AZURE_OPENAI_ENDPOINT should raise ValueError."""
        with patch.dict("os.environ", {"AZURE_OPENAI_KEY": "test-key"}, clear=True):
            import os

            os.environ.pop("AZURE_OPENAI_ENDPOINT", None)

            with pytest.raises(ValueError) as exc_info:
                get_provider("azure")

            assert "AZURE_OPENAI_ENDPOINT" in str(exc_info.value)

    def test_missing_api_key_raises(self) -> None:
        """Missing AZURE_OPENAI_KEY should raise ValueError."""
        with patch.dict(
            "os.environ", {"AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/"}, clear=True
        ):
            import os

            os.environ.pop("AZURE_OPENAI_KEY", None)

            with pytest.raises(ValueError) as exc_info:
                get_provider("azure")

            assert "AZURE_OPENAI_KEY" in str(exc_info.value)

    @patch.dict(
        "os.environ",
        {
            "AZURE_OPENAI_KEY": "test-key",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        },
    )
    @patch("backend.providers.llm.aiohttp")
    def test_default_deployment(self, mock_aiohttp: MagicMock) -> None:
        """AzureOpenAIProvider should use default model 'gpt-4o'."""
        provider = get_provider("azure")

        assert provider.default_model == "gpt-4o"

    @patch.dict(
        "os.environ",
        {
            "AZURE_OPENAI_KEY": "test-key",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        },
    )
    @patch("backend.providers.llm.aiohttp")
    def test_custom_deployment(self, mock_aiohttp: MagicMock) -> None:
        """AzureOpenAIProvider should use custom deployment from config."""
        provider = get_provider("azure", {"deployment": "gpt-4"})

        assert provider.deployment_name == "gpt-4"


# ==============================================================================
# Tests for LLMProvider abstract base class
# ==============================================================================
class TestLLMProviderABC:
    """Tests for the LLMProvider abstract base class."""

    def test_cannot_instantiate_directly(self) -> None:
        """LLMProvider should not be instantiable directly."""
        with pytest.raises(TypeError) as exc_info:
            LLMProvider()  # type: ignore[abstract]

        assert "abstract" in str(exc_info.value).lower()

    def test_has_abstract_generate_method(self) -> None:
        """LLMProvider should have abstract generate method."""
        from abc import ABC

        assert issubclass(LLMProvider, ABC)
        assert hasattr(LLMProvider, "generate")

    def test_has_abstract_embed_method(self) -> None:
        """LLMProvider should have abstract embed method."""
        assert hasattr(LLMProvider, "embed")

    def test_has_abstract_get_provider_name_method(self) -> None:
        """LLMProvider should have abstract get_provider_name method."""
        assert hasattr(LLMProvider, "get_provider_name")
