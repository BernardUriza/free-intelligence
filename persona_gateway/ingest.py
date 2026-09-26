"""Message ingestion — a Discord message's attachments → runner-ready inputs.

Readable attachments (images, text, PDFs) become Anthropic content blocks via
the shared processor.

Audio is the host's business IN A GUILD: the host owns reception and therefore
owns transcription (2026-07-23), shipping the words on the `/invite` wire, so a
guild audio attachment is only classified here to keep it out of the document
lane. The ONE exception is a DM, where that doctrine cannot be satisfied by
anyone: Discord isolates DM channels per bot user, so the host is structurally
DEAF there — it never sees the message and never issues an /invite. Before this,
a voice note in a DM produced total silence (no reply, no "…", no reaction, not
even a `last_message_seen` stamp for /health), and a DM is precisely where a
phone user sends audio. So the gateway transcribes ONLY when `guild is None`;
in a guild it still touches no STT.
"""

from __future__ import annotations

import contextlib

import discord
import structlog

from khimeras_shared.attachments import (
    MAX_DOCUMENTS_PER_MESSAGE,
    MAX_IMAGES_PER_MESSAGE,
    cap_documents,
    cap_images,
    process_attachments,
)
from khimeras_shared.prompts import SHARED_PROMPTS_DIR, PromptCache, load_prompt
from khimeras_shared.stt import (
    DEFAULT_AUDIO_CONTENT_TYPE,
    SusurroSttClient,
    is_audio_attachment,
    transcribe_voice_message,
)
from shared.personas import Persona

log = structlog.get_logger()

_PROMPT_CACHE: PromptCache = {}


class MessageIngest:
    """Turns one message's readable attachments into blocks for the runner."""

    def __init__(self, persona: Persona, stt_client: SusurroSttClient | None = None) -> None:
        self.persona = persona
        self._stt_client = stt_client

    async def dm_voice_transcript(self, message: discord.Message) -> str:
        """Words spoken in a DM voice note, or "" when it does not apply.

        Guild messages return "" untouched — there the host is the only
        transcriber and this must never become a second consumer of susurro.
        Fail-soft everywhere else: no client, no audio, or a dead susurro
        degrades to "" (the pre-existing silent behaviour), never a broken turn.
        """
        if getattr(message, "guild", None) is not None:
            return ""
        if self._stt_client is None or not getattr(message, "attachments", None):
            return ""
        parts: list[str] = []
        for attachment in message.attachments:
            if not self.is_audio_attachment(attachment, message):
                continue
            try:
                audio = await attachment.read()
                transcript = await transcribe_voice_message(
                    audio,
                    base_url=self._stt_client.base_url,
                    api_key=self._stt_client.api_key,
                    content_type=getattr(attachment, "content_type", None) or DEFAULT_AUDIO_CONTENT_TYPE,
                )
            except Exception:
                log.warning("persona_gateway_dm_stt_failed", persona_id=self.persona.persona_id, exc_info=True)
                continue
            if transcript:
                parts.append(str(transcript))
        if parts:
            log.info(
                "persona_gateway_dm_stt_transcribed",
                persona_id=self.persona.persona_id,
                parts=len(parts),
                length=sum(len(p) for p in parts),
            )
        return "\n".join(parts)

    async def attachment_blocks(self, message: discord.Message) -> list[dict]:
        """Image/document attachments of the summoning message → Anthropic blocks.

        Reuses the shared processor (images by reference to AIRE, text/pdf
        inline, in-character rejection notices). The blocks ride the final user
        message; `AgentRunnerClient` extracts them and the runner builds the
        turn — same E2E path Insult uses, so siblings finally SEE images (P0
        2026-07-07). Invite turns feed their fetched trigger message through here
        too (2026-07-16).

        More than ``MAX_IMAGES_PER_MESSAGE`` images: the first N ride and a
        trailing TEXT block carries the note (`prompts_md/images_over_cap_note.md`)
        so the persona tells the user in character. It is a text block on purpose —
        the runner client folds every text block of the last message into the
        turn's text, on the mention path and the invite path alike (PR #97).
        """
        if not message.attachments:
            return []
        readable = [att for att in message.attachments if not self.is_audio_attachment(att, message)]
        if not readable:
            return []
        readable, over_cap = cap_images(readable)
        readable, extra_docs = cap_documents(readable)
        blocks, errors = await process_attachments(readable)
        if extra_docs:
            errors.append(
                f"Solo leo {MAX_DOCUMENTS_PER_MESSAGE} archivos por mensaje; no lei: {', '.join(extra_docs)}. "
                "Mandalos en otro mensaje."
            )
        if over_cap:
            log.warning(
                "persona_gateway_attachments_capped",
                persona_id=self.persona.persona_id,
                discord_message_id=str(getattr(message, "id", "")),
                max_images=MAX_IMAGES_PER_MESSAGE,
                dropped=over_cap,
            )
            note = load_prompt(SHARED_PROMPTS_DIR, "images_over_cap_note", _PROMPT_CACHE).format(
                total=MAX_IMAGES_PER_MESSAGE + over_cap, max=MAX_IMAGES_PER_MESSAGE, dropped=over_cap
            )
            blocks = [*blocks, {"type": "text", "text": note}]
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
