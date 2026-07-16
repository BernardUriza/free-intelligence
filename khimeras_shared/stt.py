"""Shared susurro-gateway STT — Discord audio bytes → transcript text.

The susurro gateway exposes ``POST /v1/stt?language=es`` with bearer auth and a
raw audio body (not multipart). Discord voice messages are OGG/opus, so callers
default to ``Content-Type: audio/ogg``. The response JSON is
``{"success", "transcript", "engine"}``: the text lives in ``transcript``, not
``text``.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog

log = structlog.get_logger()

STT_TIMEOUT_S = 30.0
DEFAULT_AUDIO_CONTENT_TYPE = "audio/ogg"


@dataclass(frozen=True)
class SusurroSttClient:
    """Immutable handle for the susurro STT endpoint: a base URL + bearer key."""

    base_url: str
    api_key: str


class SttTranscript(str):
    """Transcript string carrying the engine for gateway logs."""

    engine: str | None

    def __new__(cls, value: str, *, engine: str | None = None) -> SttTranscript:
        obj = str.__new__(cls, value)
        obj.engine = engine
        return obj


def build_susurro_stt_client(*, base_url: str, api_key: str) -> SusurroSttClient | None:
    """Build the susurro STT client, or ``None`` when unconfigured."""
    if not base_url or not api_key:
        return None
    return SusurroSttClient(base_url=base_url.rstrip("/"), api_key=api_key)


async def transcribe_voice_message(
    audio_data: bytes,
    *,
    base_url: str,
    api_key: str,
    language: str = "es",
    content_type: str = DEFAULT_AUDIO_CONTENT_TYPE,
) -> str | None:
    """Transcribe audio bytes via susurro STT.

    Contract: ``POST {base_url}/v1/stt?language=es`` with bearer auth,
    ``Content-Type`` for the raw audio bytes, and JSON response text read from
    ``transcript`` (not ``text``). Returns ``None`` when unconfigured, when the
    transcript is empty, or on any exception so a Discord turn never crashes.
    """
    if not base_url or not api_key:
        log.warning("susurro_stt_not_configured")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": content_type or DEFAULT_AUDIO_CONTENT_TYPE,
    }
    try:
        async with httpx.AsyncClient(timeout=STT_TIMEOUT_S) as http:
            response = await http.post(
                f"{base_url.rstrip('/')}/v1/stt",
                params={"language": language},
                headers=headers,
                content=audio_data,
            )
            response.raise_for_status()
            data = response.json()

        text = (data.get("transcript") or "").strip()
        if not text:
            log.warning("susurro_stt_empty_transcription", engine=data.get("engine"))
            return None

        engine = data.get("engine")
        log.info("susurro_stt_transcribed", length=len(text), engine=engine)
        return SttTranscript(text, engine=engine)
    except Exception as exc:
        log.error("susurro_stt_failed", error=str(exc), error_type=type(exc).__name__)
        return None


__all__ = [
    "DEFAULT_AUDIO_CONTENT_TYPE",
    "STT_TIMEOUT_S",
    "SttTranscript",
    "SusurroSttClient",
    "build_susurro_stt_client",
    "transcribe_voice_message",
]
