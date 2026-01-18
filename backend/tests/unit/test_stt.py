"""Unit tests for STT providers.

Tests provider logic WITHOUT making real API calls.
Uses mocks for external dependencies.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pathlib import Path


# =============================================================================
# STTProviderType Tests
# =============================================================================
class TestSTTProviderType:
    """Tests for STTProviderType enum."""

    def test_azure_whisper_exists(self) -> None:
        """Azure Whisper provider type exists."""
        from backend.providers.stt import STTProviderType

        assert STTProviderType.AZURE_WHISPER.value == "azure_whisper"

    def test_provider_type_count(self) -> None:
        """Only one provider type (Azure Whisper)."""
        from backend.providers.stt import STTProviderType

        assert len(STTProviderType) == 1


# =============================================================================
# STTResponse Tests
# =============================================================================
class TestSTTResponse:
    """Tests for STTResponse dataclass."""

    def test_response_creation(self) -> None:
        """STTResponse can be created with all fields."""
        from backend.providers.stt import STTResponse

        response = STTResponse(
            text="Hello world",
            segments=[{"start": 0, "end": 1, "text": "Hello world"}],
            language="en",
            duration=1.5,
            confidence=0.95,
            provider="azure_whisper",
            latency_ms=500.0,
            metadata={"endpoint": "https://example.com"},
        )

        assert response.text == "Hello world"
        assert response.language == "en"
        assert response.duration == 1.5
        assert response.confidence == 0.95
        assert response.provider == "azure_whisper"
        assert response.latency_ms == 500.0
        assert len(response.segments) == 1

    def test_response_optional_fields(self) -> None:
        """STTResponse works with optional fields as None."""
        from backend.providers.stt import STTResponse

        response = STTResponse(
            text="Test",
            segments=[],
            language="es",
            duration=0.0,
            confidence=0.0,
            provider="test",
        )

        assert response.latency_ms is None
        assert response.metadata is None


# =============================================================================
# AzureWhisperProvider Tests (Unit - Mocked)
# =============================================================================
class TestAzureWhisperProviderInit:
    """Tests for AzureWhisperProvider initialization."""

    def test_init_requires_endpoint(self) -> None:
        """Raises if AZURE_OPENAI_ENDPOINT not set."""
        from backend.providers.stt import AzureWhisperProvider

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
                AzureWhisperProvider()

    def test_init_requires_api_key(self) -> None:
        """Raises if AZURE_OPENAI_API_KEY not set."""
        from backend.providers.stt import AzureWhisperProvider

        with patch.dict(
            "os.environ",
            {"AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com"},
            clear=True,
        ):
            with pytest.raises(ValueError, match="AZURE_OPENAI_API_KEY"):
                AzureWhisperProvider()

    def test_init_success_with_env_vars(self) -> None:
        """Successfully initializes with env vars."""
        from backend.providers.stt import AzureWhisperProvider

        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key-123",
            },
            clear=True,
        ):
            provider = AzureWhisperProvider()
            assert provider.endpoint == "https://test.openai.azure.com"
            assert provider.api_key == "test-key-123"
            assert provider.deployment == "whisper"
            assert provider.api_version == "2024-02-01"

    def test_init_with_custom_config(self) -> None:
        """Uses config values when provided."""
        from backend.providers.stt import AzureWhisperProvider

        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key-123",
            },
            clear=True,
        ):
            provider = AzureWhisperProvider(
                config={
                    "deployment": "whisper-large",
                    "api_version": "2024-06-01",
                    "timeout_seconds": 60,
                }
            )
            assert provider.deployment == "whisper-large"
            assert provider.api_version == "2024-06-01"
            assert provider.timeout == 60

    def test_get_provider_name(self) -> None:
        """Returns correct provider name."""
        from backend.providers.stt import AzureWhisperProvider

        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key-123",
            },
            clear=True,
        ):
            provider = AzureWhisperProvider()
            assert provider.get_provider_name() == "azure_whisper"


class TestAzureWhisperProviderTranscribe:
    """Tests for AzureWhisperProvider.transcribe() method."""

    def test_transcribe_file_not_found(self) -> None:
        """Raises FileNotFoundError for missing file."""
        from backend.providers.stt import AzureWhisperProvider

        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key-123",
            },
            clear=True,
        ):
            provider = AzureWhisperProvider()
            with pytest.raises(FileNotFoundError, match="Audio file not found"):
                provider.transcribe("/nonexistent/path/audio.mp3")


# =============================================================================
# Factory Function Tests
# =============================================================================
class TestGetSTTProvider:
    """Tests for get_stt_provider factory function."""

    def test_default_returns_azure_whisper(self) -> None:
        """Default provider is Azure Whisper."""
        from backend.providers.stt import AzureWhisperProvider, get_stt_provider

        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key-123",
            },
            clear=True,
        ):
            provider = get_stt_provider()
            assert isinstance(provider, AzureWhisperProvider)

    def test_explicit_azure_whisper(self) -> None:
        """Explicitly requesting azure_whisper works."""
        from backend.providers.stt import AzureWhisperProvider, get_stt_provider

        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key-123",
            },
            clear=True,
        ):
            provider = get_stt_provider("azure_whisper")
            assert isinstance(provider, AzureWhisperProvider)

    def test_legacy_deepgram_falls_back_to_azure(self) -> None:
        """Legacy 'deepgram' request falls back to Azure with warning."""
        from backend.providers.stt import AzureWhisperProvider, get_stt_provider

        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key-123",
            },
            clear=True,
        ):
            provider = get_stt_provider("deepgram")
            assert isinstance(provider, AzureWhisperProvider)

    def test_unknown_provider_raises(self) -> None:
        """Unknown provider raises ValueError."""
        from backend.providers.stt import get_stt_provider

        with pytest.raises(ValueError, match="Unknown STT provider"):
            get_stt_provider("unknown_provider")

    def test_case_insensitive(self) -> None:
        """Provider name is case-insensitive."""
        from backend.providers.stt import AzureWhisperProvider, get_stt_provider

        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key-123",
            },
            clear=True,
        ):
            provider = get_stt_provider("AZURE_WHISPER")
            assert isinstance(provider, AzureWhisperProvider)

    def test_passes_config_to_provider(self) -> None:
        """Config dict is passed to provider."""
        from backend.providers.stt import get_stt_provider

        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key-123",
            },
            clear=True,
        ):
            provider = get_stt_provider(
                "azure_whisper",
                config={"deployment": "whisper-v2", "timeout_seconds": 45},
            )
            assert provider.deployment == "whisper-v2"
            assert provider.timeout == 45
