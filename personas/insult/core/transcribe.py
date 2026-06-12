"""Voice message transcription via Azure OpenAI Whisper.

Transcribes Discord voice messages (OGG audio) to text so Insult can
"hear" what users say. Uses the same Azure OpenAI resource as TTS.
"""

import io

import structlog
from openai import AsyncAzureOpenAI

log = structlog.get_logger()

WHISPER_TIMEOUT = 30


async def transcribe_voice_message(
    audio_data: bytes,
    *,
    endpoint: str,
    api_key: str,
    deployment: str = "whisper",
) -> str | None:
    """Transcribe OGG audio bytes via Azure OpenAI Whisper.

    Returns transcribed text, or None on failure.
    """
    if not endpoint or not api_key:
        log.warning("whisper_not_configured")
        return None

    try:
        client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2024-12-01-preview",
            timeout=WHISPER_TIMEOUT,
        )

        audio_file = io.BytesIO(audio_data)
        audio_file.name = "voice.ogg"

        response = await client.audio.transcriptions.create(
            model=deployment,
            file=audio_file,
        )

        text = response.text.strip()
        if not text:
            log.warning("whisper_empty_transcription")
            return None

        log.info("whisper_transcribed", length=len(text), preview=text[:80])
        return text

    except Exception as e:
        log.error("whisper_transcription_failed", error=str(e), error_type=type(e).__name__)
        return None
