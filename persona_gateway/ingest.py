"""Message ingestion — a Discord message's attachments → runner-ready inputs.

Two lanes out of one summoning message: readable attachments (images, text,
PDFs) become Anthropic content blocks via the shared processor, and
voice-message audio becomes text transcripts via susurro STT. The gateway's
turn builders (`_handle`, `respond_to_invite`) consume both lanes and never
touch the classification/download mechanics themselves.
"""

from __future__ import annotations

import contextlib

import discord
import structlog

from khimeras_shared.attachments import process_attachments
from khimeras_shared.stt import (
    DEFAULT_AUDIO_CONTENT_TYPE,
    SusurroSttClient,
    transcribe_voice_message,
)
from shared.personas import Persona

log = structlog.get_logger()

_VOICE_FILENAME_SUFFIXES = (".ogg", ".opus", ".mp3", ".m4a", ".wav", ".webm")


class MessageIngest:
    """Turns one message's attachments into blocks + transcripts for the runner."""

    def __init__(self, persona: Persona, stt_client: SusurroSttClient | None) -> None:
        self.persona = persona
        self._stt_client = stt_client

    async def attachment_blocks(self, message: discord.Message) -> list[dict]:
        """Image/document attachments of the summoning message → Anthropic blocks.

        Reuses Insult's shared processor (5MB cap with image compression,
        png/jpg/gif/webp + text/pdf, in-character rejection notices). The blocks
        ride the final user message; `AgentRunnerClient` extracts them and the
        runner builds the multimodal SDK input — same E2E path Insult uses, so
        siblings finally SEE images (P0 2026-07-07). Invite turns feed their
        fetched trigger message through here too (2026-07-16).
        """
        if not message.attachments:
            return []
        readable = [att for att in message.attachments if not self.is_audio_attachment(att, message)]
        if not readable:
            return []
        blocks, errors = await process_attachments(readable)
        for err in errors:
            with contextlib.suppress(discord.HTTPException):
                await message.channel.send(err)
        log.info(
            "persona_gateway_attachments_processed",
            persona_id=self.persona.persona_id,
            blocks=len(blocks),
            errors=len(errors),
        )
        return blocks

    @staticmethod
    def is_audio_attachment(attachment, message: discord.Message) -> bool:
        content_type = (getattr(attachment, "content_type", None) or "").lower()
        if content_type.startswith("audio/"):
            return True
        filename = (getattr(attachment, "filename", None) or "").lower()
        return bool(
            getattr(message.flags, "voice", False) and (not content_type or filename.endswith(_VOICE_FILENAME_SUFFIXES))
        )

    async def voice_transcripts(self, message: discord.Message) -> list[str]:
        """Voice-message audio → text via susurro STT. Empty when STT is off.

        Per-attachment failures are logged and skipped — a broken voice note must
        never kill the turn the text part of the message still deserves.
        """
        if not message.attachments or self._stt_client is None:
            return []

        transcripts: list[str] = []
        for attachment in message.attachments:
            if not self.is_audio_attachment(attachment, message):
                continue
            content_type = getattr(attachment, "content_type", None) or DEFAULT_AUDIO_CONTENT_TYPE
            try:
                audio_data = await attachment.read()
                transcript = await transcribe_voice_message(
                    audio_data,
                    base_url=self._stt_client.base_url,
                    api_key=self._stt_client.api_key,
                    content_type=content_type,
                )
            except Exception as exc:
                log.error(
                    "persona_gateway_stt_failed",
                    persona_id=self.persona.persona_id,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                continue
            if transcript is None:
                continue
            log.info(
                "persona_gateway_stt_transcribed",
                persona_id=self.persona.persona_id,
                length=len(transcript),
                engine=getattr(transcript, "engine", None),
            )
            transcripts.append(str(transcript))
        return transcripts
