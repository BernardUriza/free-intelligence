"""Tests for insult.core.transcribe — Whisper voice message transcription."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from personas.insult.core.transcribe import transcribe_voice_message


class TestTranscribeVoiceMessage:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_endpoint(self):
        result = await transcribe_voice_message(b"audio", endpoint="", api_key="key")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_api_key(self):
        result = await transcribe_voice_message(b"audio", endpoint="https://x.com", api_key="")
        assert result is None

    @pytest.mark.asyncio
    async def test_successful_transcription(self):
        mock_response = MagicMock()
        mock_response.text = "hola que tal"

        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

        with patch("personas.insult.core.transcribe.AsyncAzureOpenAI", return_value=mock_client):
            result = await transcribe_voice_message(
                b"fake-ogg-data",
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                deployment="whisper",
            )

        assert result == "hola que tal"
        mock_client.audio.transcriptions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_transcription_returns_none(self):
        mock_response = MagicMock()
        mock_response.text = "   "

        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

        with patch("personas.insult.core.transcribe.AsyncAzureOpenAI", return_value=mock_client):
            result = await transcribe_voice_message(
                b"fake-ogg-data",
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self):
        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create = AsyncMock(side_effect=Exception("API error"))

        with patch("personas.insult.core.transcribe.AsyncAzureOpenAI", return_value=mock_client):
            result = await transcribe_voice_message(
                b"fake-ogg-data",
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
            )

        assert result is None
