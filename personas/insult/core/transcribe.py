"""Voice-message transcription via the susurro gateway STT.

Transcribes Discord voice messages (audio bytes) to text so Insult can "hear"
what users say. Reaches the susurro gateway's ``POST /v1/stt?language=es`` (Bearer
auth, raw audio body — NOT multipart), which routes to Azure Whisper behind one
project key. The response is JSON ``{"success", "transcript", "engine"}`` — the
text lives in ``transcript`` (not ``text``).

Migrated 2026-06-19 off the direct Azure OpenAI ``whisper`` deployment (deleted).
"""

from __future__ import annotations

import httpx
import structlog

log = structlog.get_logger()

WHISPER_TIMEOUT = 30
DEFAULT_AUDIO_CONTENT_TYPE = "audio/ogg"  # Discord voice messages are OGG/opus


async def transcribe_voice_message(
    audio_data: bytes,
    *,
    base_url: str,
    api_key: str,
    language: str = "es",
    content_type: str = DEFAULT_AUDIO_CONTENT_TYPE,
) -> str | None:
    """Transcribe audio bytes via the susurro gateway STT.

    Returns the transcribed text, or ``None`` on any failure / empty result.
    """
    if not base_url or not api_key:
        log.warning("whisper_not_configured")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": content_type or DEFAULT_AUDIO_CONTENT_TYPE,
    }
    url = f"{base_url.rstrip('/')}/v1/stt"
    try:
        async with httpx.AsyncClient(timeout=WHISPER_TIMEOUT) as http:
            response = await http.post(
                url,
                params={"language": language},
                headers=headers,
                content=audio_data,
            )
            response.raise_for_status()
            data = response.json()

        text = (data.get("transcript") or "").strip()
        if not text:
            log.warning("whisper_empty_transcription", engine=data.get("engine"))
            return None

        log.info("whisper_transcribed", length=len(text), preview=text[:80], engine=data.get("engine"))
        return text

    except Exception as e:
        log.error("whisper_transcription_failed", error=str(e), error_type=type(e).__name__)
        return None
