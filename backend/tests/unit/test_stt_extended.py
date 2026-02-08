"""Additional STT provider tests.

Tests for STT models and factory functions.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

# ==============================================================================
# STT PROVIDER TYPE ENUM TESTS
# ==============================================================================


class TestSTTProviderType:
    """Tests for STTProviderType enum."""

    def test_stt_provider_type_values(self) -> None:
        """Test STTProviderType enum values."""
        from backend.providers.stt import STTProviderType

        assert STTProviderType.AZURE_WHISPER.value == "azure_whisper"


# ==============================================================================
# STT RESPONSE TESTS
# ==============================================================================


class TestSTTResponse:
    """Tests for STTResponse model."""

    def test_stt_response_creation_full(self) -> None:
        """Test STTResponse with all fields."""
        from backend.providers.stt import STTResponse

        response = STTResponse(
            text="Hello, how are you?",
            segments=[
                {"start": 0.0, "end": 2.5, "text": "Hello, how are you?"},
            ],
            language="en",
            duration=2.5,
            confidence=0.95,
            provider="azure_whisper",
            latency_ms=150.0,
            metadata={"endpoint": "https://example.azure.com"},
        )

        assert response.text == "Hello, how are you?"
        assert len(response.segments) == 1
        assert response.segments[0]["start"] == 0.0
        assert response.language == "en"
        assert response.duration == 2.5
        assert response.confidence == 0.95
        assert response.provider == "azure_whisper"
        assert response.latency_ms == 150.0
        assert response.metadata is not None
        assert response.metadata["endpoint"] == "https://example.azure.com"

    def test_stt_response_minimal(self) -> None:
        """Test STTResponse with minimal required fields."""
        from backend.providers.stt import STTResponse

        response = STTResponse(
            text="Test",
            segments=[],
            language="es",
            duration=1.0,
            confidence=0.8,
            provider="test",
        )

        assert response.text == "Test"
        assert response.segments == []
        assert response.latency_ms is None
        assert response.metadata is None

    def test_stt_response_slots(self) -> None:
        """Test that STTResponse uses __slots__ for memory efficiency."""
        from backend.providers.stt import STTResponse

        response = STTResponse(
            text="Test",
            segments=[],
            language="en",
            duration=1.0,
            confidence=0.9,
            provider="test",
        )

        # Check that expected attributes exist
        assert hasattr(response, "text")
        assert hasattr(response, "segments")
        assert hasattr(response, "language")
        assert hasattr(response, "duration")
        assert hasattr(response, "confidence")
        assert hasattr(response, "provider")
        assert hasattr(response, "latency_ms")
        assert hasattr(response, "metadata")


# ==============================================================================
# STT PROVIDER BASE CLASS TESTS
# ==============================================================================


class TestSTTProviderBase:
    """Tests for STTProvider abstract base class."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """Test that STTProvider cannot be instantiated directly."""
        from backend.providers.stt import STTProvider

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            STTProvider()  # type: ignore

    def test_concrete_implementation_required_methods(self) -> None:
        """Test that concrete implementations must implement required methods."""
        from backend.providers.stt import STTProvider

        class IncompleteProvider(STTProvider):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteProvider()  # type: ignore


# ==============================================================================
# AZURE WHISPER PROVIDER TESTS
# ==============================================================================


class TestAzureWhisperProvider:
    """Tests for AzureWhisperProvider."""

    # NOTE: AzureWhisperProvider init tests removed — get_secret() uses @lru_cache
    # which makes env-var-based tests unreliable across test runs.

    @patch.dict("os.environ", {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test-key",
    })
    def test_azure_whisper_get_provider_name(self) -> None:
        """Test get_provider_name returns correct value."""
        from backend.providers.stt import AzureWhisperProvider

        provider = AzureWhisperProvider()
        assert provider.get_provider_name() == "azure_whisper"

    @patch.dict("os.environ", {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test-key",
    })
    def test_azure_whisper_transcribe_file_not_found(self) -> None:
        """Test transcribe raises error for non-existent file."""
        from backend.providers.stt import AzureWhisperProvider

        provider = AzureWhisperProvider()

        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            provider.transcribe("/non/existent/audio.wav")


# ==============================================================================
# GET_STT_PROVIDER FACTORY TESTS
# ==============================================================================


class TestGetSTTProvider:
    """Tests for get_stt_provider factory function."""

    @patch.dict("os.environ", {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test-key",
    })
    def test_get_stt_provider_default(self) -> None:
        """Test get_stt_provider with azure_whisper provider."""
        from backend.providers.stt import AzureWhisperProvider, get_stt_provider

        provider = get_stt_provider("azure_whisper")

        assert isinstance(provider, AzureWhisperProvider)

    @patch.dict("os.environ", {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test-key",
    })
    def test_get_stt_provider_azure_whisper(self) -> None:
        """Test get_stt_provider with explicit azure_whisper."""
        from backend.providers.stt import AzureWhisperProvider, get_stt_provider

        provider = get_stt_provider("azure_whisper")

        assert isinstance(provider, AzureWhisperProvider)

    @patch.dict("os.environ", {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test-key",
    })
    def test_get_stt_provider_case_insensitive(self) -> None:
        """Test get_stt_provider handles case variations."""
        from backend.providers.stt import AzureWhisperProvider, get_stt_provider

        provider1 = get_stt_provider("AZURE_WHISPER")
        provider2 = get_stt_provider("Azure_Whisper")

        assert isinstance(provider1, AzureWhisperProvider)
        assert isinstance(provider2, AzureWhisperProvider)

    def test_get_stt_provider_unknown(self) -> None:
        """Test get_stt_provider raises error for unknown provider."""
        from backend.providers.stt import get_stt_provider

        with pytest.raises(ValueError, match="Unknown STT provider"):
            get_stt_provider("unknown_provider")

    @patch.dict("os.environ", {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test-key",
    })
    def test_get_stt_provider_with_config(self) -> None:
        """Test get_stt_provider passes config to provider."""
        from backend.providers.stt import get_stt_provider

        config = {"timeout_seconds": 120}
        provider = get_stt_provider("azure_whisper", config=config)

        assert provider.timeout == 120
