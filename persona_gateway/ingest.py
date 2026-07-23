"""Message ingestion — a Discord message's attachments → runner-ready inputs.

Readable attachments (images, text, PDFs) become Anthropic content blocks via
the shared processor. Audio is NOT this module's business: the host owns
reception and therefore owns transcription (2026-07-23), and ships the words on
the `/invite` wire — so audio attachments are only classified here, to keep them
out of the document lane.
"""

from __future__ import annotations

import contextlib

import discord
import structlog

from khimeras_shared.attachments import process_attachments
from khimeras_shared.stt import is_audio_attachment
from shared.personas import Persona

log = structlog.get_logger()


class MessageIngest:
    """Turns one message's readable attachments into blocks for the runner."""

    def __init__(self, persona: Persona) -> None:
        self.persona = persona

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
        return is_audio_attachment(
            content_type=getattr(attachment, "content_type", None),
            filename=getattr(attachment, "filename", None),
            voice_message=bool(getattr(message.flags, "voice", False)),
        )
