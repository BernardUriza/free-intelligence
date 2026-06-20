"""Voice-package Protocols — host-visible contract for the transcription seam.

Kept in the voice package so the audio-to-text capability boundary is
self-contained and does not pollute the general turn-pipeline ports.

The adapter that satisfies this Protocol lives in ``insult.composition``
(the composition root); ``insult.cogs.chat.voice`` calls it through
``default_transcription_port()`` so it never imports
``insult.core.transcribe`` directly — closing the last
``host → smart`` import-boundary violation.
"""

from __future__ import annotations

from typing import Protocol


class TranscriptionPort(Protocol):
    """Capability port: audio bytes → transcribed text.

    Implemented by ``_CoreTranscriptionAdapter`` in ``insult.composition``.
    """

    async def transcribe(
        self,
        audio_data: bytes,
        *,
        base_url: str,
        api_key: str,
        language: str = "es",
        content_type: str = "audio/ogg",
    ) -> str | None: ...
