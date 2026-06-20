"""Tests for insult.core.transcribe — voice-message STT via the susurro gateway.

The gateway exposes ``POST /v1/stt?language=es`` (Bearer auth, raw audio body,
JSON ``{"success", "transcript", "engine"}``). These pin: the None-when-unconfigured
posture, the request shape (URL, header, params, raw body), parsing the
``transcript`` field (NOT ``text``), and failing safe to None on error.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from personas.insult.core.transcribe import transcribe_voice_message


def _mock_async_client(*, json_body: dict | None = None, raise_status: Exception | None = None):
    """MagicMock standing in for ``httpx.AsyncClient(...)`` as an async context
    manager. Returns ``(factory, post_mock)``."""
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


class TestTranscribeVoiceMessage:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_base_url(self):
        result = await transcribe_voice_message(b"audio", base_url="", api_key="key")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_api_key(self):
        result = await transcribe_voice_message(b"audio", base_url="https://sus.example.com", api_key="")
        assert result is None

    @pytest.mark.asyncio
    async def test_successful_transcription_reads_transcript_field(self):
        factory, post = _mock_async_client(
            json_body={"success": True, "transcript": "hola que tal", "engine": "azure-whisper"}
        )

        with patch("personas.insult.core.transcribe.httpx.AsyncClient", factory):
            result = await transcribe_voice_message(
                b"fake-ogg-data",
                base_url="https://sus.example.com",
                api_key="sk-secret",
            )

        assert result == "hola que tal"
        post.assert_awaited_once()
        url = post.await_args.args[0] if post.await_args.args else post.await_args.kwargs["url"]
        assert url == "https://sus.example.com/v1/stt"
        kwargs = post.await_args.kwargs
        assert kwargs["headers"]["Authorization"] == "Bearer sk-secret"
        assert kwargs["params"] == {"language": "es"}
        # Raw audio bytes are the body — NOT multipart.
        assert kwargs.get("content") == b"fake-ogg-data"

    @pytest.mark.asyncio
    async def test_passes_content_type_through(self):
        factory, post = _mock_async_client(json_body={"success": True, "transcript": "x"})

        with patch("personas.insult.core.transcribe.httpx.AsyncClient", factory):
            await transcribe_voice_message(
                b"d",
                base_url="https://sus.example.com",
                api_key="k",
                content_type="audio/mpeg",
            )

        assert post.await_args.kwargs["headers"]["Content-Type"] == "audio/mpeg"

    @pytest.mark.asyncio
    async def test_empty_transcript_returns_none(self):
        factory, _post = _mock_async_client(json_body={"success": True, "transcript": "   "})

        with patch("personas.insult.core.transcribe.httpx.AsyncClient", factory):
            result = await transcribe_voice_message(b"d", base_url="https://sus.example.com", api_key="k")

        assert result is None

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self):
        factory, _post = _mock_async_client(raise_status=Exception("502"))

        with patch("personas.insult.core.transcribe.httpx.AsyncClient", factory):
            result = await transcribe_voice_message(b"d", base_url="https://sus.example.com", api_key="k")

        assert result is None
