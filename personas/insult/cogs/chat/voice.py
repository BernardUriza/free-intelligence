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
        audio_data = await message.attachments[0].read()
        audio_bytes = len(audio_data)
        result = await port.transcribe(
            audio_data,
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key.get_secret_value(),
            deployment=settings.azure_openai_whisper_deployment,
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
