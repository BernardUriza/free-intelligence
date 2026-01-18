"""Integration tests for STT providers.

These tests use REAL audio files and REAL API calls.
Marked as 'integration' - not run in CI by default.

Run with: pytest -m integration backend/tests/integration/test_stt_integration.py -v
"""

from __future__ import annotations

import os
import pytest
from dotenv import load_dotenv
from pathlib import Path

# Load .env BEFORE checking credentials
load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

# Sample chunk path
SAMPLE_CHUNK = Path("/Users/bernardurizaorozco/Desktop/Patient-Centered Chunks/chunk_000.mp3")


@pytest.mark.integration
@pytest.mark.skipif(
    not AZURE_OPENAI_API_KEY or not AZURE_OPENAI_ENDPOINT,
    reason="Azure OpenAI credentials not set",
)
@pytest.mark.skipif(
    not SAMPLE_CHUNK.exists(),
    reason=f"Sample audio not found: {SAMPLE_CHUNK}",
)
class TestAzureWhisperIntegration:
    """Integration tests for Azure Whisper STT provider."""

    def test_transcribe_mp3_chunk(self) -> None:
        """Transcribe a real MP3 audio chunk."""
        from backend.providers.stt import AzureWhisperProvider, STTResponse

        provider = AzureWhisperProvider()
        # Audio is in English - let Whisper auto-detect or specify "en"
        result = provider.transcribe(SAMPLE_CHUNK, language="en")

        # Verify response structure
        assert isinstance(result, STTResponse)
        assert result.provider == "azure_whisper"
        assert result.text  # Non-empty text
        assert len(result.text) > 10  # Reasonable transcript
        # Azure may return 'es' or detect language automatically
        assert result.language is not None
        # Duration may be 0 if Azure doesn't return it (API limitation)
        assert result.duration >= 0
        assert result.confidence >= 0
        assert result.latency_ms is not None and result.latency_ms > 0

        print(f"\n📝 Transcription ({len(result.text)} chars):")
        print(f"   {result.text[:200]}...")
        print(f"⏱️  Latency: {result.latency_ms:.0f}ms")
        print(f"📊 Confidence: {result.confidence:.2f}")

    def test_transcribe_multiple_chunks(self) -> None:
        """Transcribe 3 chunks and verify consistency."""
        from backend.providers.stt import AzureWhisperProvider

        chunks_dir = SAMPLE_CHUNK.parent
        chunks = sorted(chunks_dir.glob("chunk_00*.mp3"))[:3]

        provider = AzureWhisperProvider()
        results = []

        for chunk in chunks:
            # Audio is in English
            result = provider.transcribe(chunk, language="en")
            results.append(result)
            print(f"\n🎵 {chunk.name}: {result.text[:100]}...")

        # All should return valid responses
        assert len(results) == 3
        for r in results:
            assert r.text
            assert r.provider == "azure_whisper"

    def test_get_provider_name(self) -> None:
        """Provider returns correct name."""
        from backend.providers.stt import AzureWhisperProvider

        provider = AzureWhisperProvider()
        assert provider.get_provider_name() == "azure_whisper"


@pytest.mark.integration
@pytest.mark.skipif(
    not AZURE_OPENAI_API_KEY or not AZURE_OPENAI_ENDPOINT,
    reason="Azure OpenAI credentials not set",
)
class TestSTTFactory:
    """Test the STT provider factory."""

    def test_get_default_provider(self) -> None:
        """Factory returns Azure Whisper by default."""
        from backend.providers.stt import AzureWhisperProvider, get_stt_provider

        provider = get_stt_provider()
        assert isinstance(provider, AzureWhisperProvider)

    def test_get_azure_whisper_explicitly(self) -> None:
        """Factory returns Azure Whisper when requested."""
        from backend.providers.stt import AzureWhisperProvider, get_stt_provider

        provider = get_stt_provider("azure_whisper")
        assert isinstance(provider, AzureWhisperProvider)

    def test_unknown_provider_raises(self) -> None:
        """Factory raises for unknown provider."""
        from backend.providers.stt import get_stt_provider

        with pytest.raises(ValueError, match="Unknown STT provider"):
            get_stt_provider("unknown_provider")
