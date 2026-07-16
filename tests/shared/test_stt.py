"""Tests for khimeras_shared.stt — voice-message STT via susurro.

The gateway exposes ``POST /v1/stt?language=es`` (Bearer auth, raw audio body,
JSON ``{"success", "transcript", "engine"}``). These pin the unconfigured
posture, request shape, ``transcript`` parsing, and fail-safe error behavior.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from khimeras_shared.stt import SttTranscript, build_susurro_stt_client, transcribe_voice_message


def _mock_async_client(*, json_body: dict | None = None, raise_status: Exception | None = None):
    """Build an ``httpx.AsyncClient`` mock usable as an async context manager."""
    resp = MagicMock()
    resp.json = MagicMock(return_value=json_body or {})
    if raise_status is not None:
        resp.raise_for_status = MagicMock(side_effect=raise_status)
    else:
        resp.raise_for_status = MagicMock()

    post = AsyncMock(return_value=resp)
    http = MagicMock()
    http.post = post
    http.__aenter__ = AsyncMock(return_value=http)
    http.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=http), post


class TestBuildSusurroSttClient:
    def test_none_when_base_url_missing(self):
        """STT stays disabled when susurro URL is missing."""
        assert build_susurro_stt_client(base_url="", api_key="k") is None

    def test_none_when_key_missing(self):
        """STT stays disabled when susurro key is missing."""
        assert build_susurro_stt_client(base_url="https://sus.example.com", api_key="") is None

    def test_strips_trailing_slash_from_base_url(self):
        """Base URL is normalized before request construction."""
        client = build_susurro_stt_client(base_url="https://sus.example.com/", api_key="k")

        assert client is not None
        assert client.base_url == "https://sus.example.com"


class TestTranscribeVoiceMessage:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_base_url(self):
        """Missing base URL returns None without an HTTP call."""
        result = await transcribe_voice_message(b"audio", base_url="", api_key="key")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_api_key(self):
        """Missing API key returns None without an HTTP call."""
        result = await transcribe_voice_message(b"audio", base_url="https://sus.example.com", api_key="")

        assert result is None

    @pytest.mark.asyncio
    async def test_successful_transcription_reads_transcript_field(self):
        """Successful STT posts raw bytes and reads transcript, not text."""
        factory, post = _mock_async_client(
            json_body={
                "success": True,
                "transcript": "hola que tal",
                "text": "campo equivocado",
                "engine": "azure-whisper",
            }
        )

        with patch("khimeras_shared.stt.httpx.AsyncClient", factory):
            result = await transcribe_voice_message(
                b"fake-ogg-data",
                base_url="https://sus.example.com",
                api_key="sk-secret",
            )

        assert result == "hola que tal"
        assert isinstance(result, SttTranscript)
        assert result.engine == "azure-whisper"
        post.assert_awaited_once()
        url = post.await_args.args[0] if post.await_args.args else post.await_args.kwargs["url"]
        assert url == "https://sus.example.com/v1/stt"
        kwargs = post.await_args.kwargs
        assert kwargs["headers"]["Authorization"] == "Bearer sk-secret"
        assert kwargs["headers"]["Content-Type"] == "audio/ogg"
        assert kwargs["params"] == {"language": "es"}
        assert kwargs.get("content") == b"fake-ogg-data"

    @pytest.mark.asyncio
    async def test_passes_content_type_through(self):
        """Caller-provided content type is sent unchanged."""
        factory, post = _mock_async_client(json_body={"success": True, "transcript": "x"})

        with patch("khimeras_shared.stt.httpx.AsyncClient", factory):
            await transcribe_voice_message(
                b"d",
                base_url="https://sus.example.com",
                api_key="k",
                content_type="audio/mpeg",
            )

        assert post.await_args.kwargs["headers"]["Content-Type"] == "audio/mpeg"

    @pytest.mark.asyncio
    async def test_empty_transcript_returns_none(self):
        """Blank transcript is treated as no transcription."""
        factory, _post = _mock_async_client(json_body={"success": True, "transcript": "   "})

        with patch("khimeras_shared.stt.httpx.AsyncClient", factory):
            result = await transcribe_voice_message(b"d", base_url="https://sus.example.com", api_key="k")

        assert result is None

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self):
        """HTTP errors fail safe to None."""
        factory, _post = _mock_async_client(raise_status=Exception("502"))

        with patch("khimeras_shared.stt.httpx.AsyncClient", factory):
            result = await transcribe_voice_message(b"d", base_url="https://sus.example.com", api_key="k")

        assert result is None
