"""Voice-message transcription via Azure OpenAI Whisper.

Only entry point: `transcribe_voice(message, settings)` — returns the
transcribed string, or None on any failure (with a log.exception). The
backend is reached through the ``TranscriptionPort`` (see
``insult.cogs.voice.ports``) via ``insult.composition.default_transcription_port()``,
keeping this module free of direct ``insult.core.transcribe`` imports.
"""

from __future__ import annotations

import time

import discord
import structlog

log = structlog.get_logger()


async def transcribe_voice(message: discord.Message, settings) -> str | None:
    """Read the first attachment as audio and send it through Whisper."""
    from personas.insult.composition import default_transcription_port

    port = default_transcription_port()
    started = time.monotonic()
    audio_bytes = 0
    try:
        attachment = message.attachments[0]
        audio_data = await attachment.read()
        audio_bytes = len(audio_data)
        result = await port.transcribe(
            audio_data,
            base_url=settings.susurro_url,
            api_key=settings.susurro_key.get_secret_value(),
            language="es",
            content_type=attachment.content_type or "audio/ogg",
        )
        log.info(
            "voice_transcription_ok",
            duration_ms=int((time.monotonic() - started) * 1000),
            audio_bytes=audio_bytes,
            text_len=len(result or ""),
            text_preview=(result or "")[:120],
        )
        return result
    except Exception:
        log.exception(
            "voice_transcription_failed",
            duration_ms=int((time.monotonic() - started) * 1000),
            audio_bytes=audio_bytes,
        )
        return None
