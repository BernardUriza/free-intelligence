"""Voice cog — TTS via Azure OpenAI, sent as audio file attachment.

React with 🔊 on any message to have the bot generate a voice clip
and send it as an MP3 file in the channel.
"""

from __future__ import annotations

import io
import re
from typing import TYPE_CHECKING

import discord
import httpx
import structlog
from discord.ext import commands
from openai import AsyncAzureOpenAI

from khimeras_shared.tts import build_azure_tts_client, should_auto_tts, split_for_tts, synthesize_azure_tts
from shared.personas.registry import sibling_bot_user_ids

if TYPE_CHECKING:
    from personas.insult.app import Container

log = structlog.get_logger()

SPEAK_EMOJI = "🔊"

# Strips the version-tag suffix that delivery.py appends to the final
# chunk of a response ("\n-# ᵛ³·⁵·XX"). We strip it before the memory
# substring lookup because memory stores the pre-chunk text without it.
_VERSION_TAG_RE = re.compile(r"\n-#\s*ᵛ.+$", re.UNICODE)


def pick_tts_voice(author_id: int | str, settings) -> tuple[str, bool]:
    """Choose the TTS voice for a message by its author.

    The VoiceCog speaks ANY 🔊'd message. ALICE-authored messages get her
    female tts-1 voice; everyone else (Insult, humans) gets the default
    male voice. Returns ``(voice, is_alice)`` — ``is_alice`` is logged so
    voice mismatches are debuggable. When ``alice_bot_user_id`` is empty the
    feature is off and everything uses the default voice.
    """
    alice_id = getattr(settings, "alice_bot_user_id", "")
    is_alice = bool(alice_id) and str(author_id) == str(alice_id)
    voice = settings.alice_tts_voice if is_alice else settings.tts_voice
    return voice, is_alice


def build_arbor_tts_payload(text: str, settings) -> dict[str, str]:
    """Payload accepted by the external arbor-tts service."""
    return {
        "text": text[:4096],
        "voice": getattr(settings, "arbor_tts_voice", "arbor") or "arbor",
        "format": "mp3",
    }


async def generate_arbor_tts_audio(text: str, settings) -> bytes:
    """Generate MP3 bytes through the external Arbor TTS service."""
    base_url = getattr(settings, "arbor_tts_url", "").rstrip("/")
    if not base_url:
        raise RuntimeError("arbor_tts_url is not configured")

    token = settings.arbor_tts_token.get_secret_value()
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"

    timeout = float(getattr(settings, "arbor_tts_timeout_seconds", 240.0))
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{base_url}/tts",
            headers=headers,
            json=build_arbor_tts_payload(text, settings),
        )
        response.raise_for_status()
        return response.content


async def resolve_full_response(
    memory,
    channel_id: str,
    chunk_text: str,
    *,
    lookback: int = 10,
) -> str | None:
    """Given a chunk of bot text a user reacted on, return the full pre-chunk
    response from memory if it can be located.

    Long bot responses get split by `delivery.py` into Discord messages of
    ≤1990 chars each. When a user reacts 🔊 on one of those chunks,
    `message.content` is only that slice — so TTS speaks ~2 min and stops.
    `turn.py` persists the full response (before chunking) in memory with
    role="assistant"; we locate it via substring match on the chunk text.

    Returns None when no assistant entry in the last `lookback` messages
    contains the chunk — caller should fall back to the chunk text.
    """
    needle = _VERSION_TAG_RE.sub("", chunk_text).strip()
    if not needle:
        return None

    try:
        recent = await memory.get_recent(channel_id, limit=lookback)
    except Exception:
        log.exception("tts_memory_lookup_failed", channel_id=channel_id)
        return None

    # `get_recent` returns oldest-first; walk newest-first so we prefer
    # the most recent turn when the same substring repeats across history.
    for entry in reversed(recent):
        if entry.get("role") != "assistant":
            continue
        content = entry.get("content", "")
        if needle in content:
            return content

    return None


class VoiceCog(commands.Cog):
    def __init__(self, container: Container):
        self.settings = container.settings
        self.bot = container.bot
        self.memory = container.memory
        self._tts_client: AsyncAzureOpenAI | None = None

    def _get_tts_client(self) -> AsyncAzureOpenAI | None:
        """Lazy-init Azure OpenAI client for TTS."""
        if self._tts_client:
            return self._tts_client
        endpoint = self.settings.azure_openai_endpoint
        key = self.settings.azure_openai_key.get_secret_value()
        self._tts_client = build_azure_tts_client(endpoint=endpoint, api_key=key)
        return self._tts_client

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """When someone reacts with 🔊, generate TTS and send as audio file.

        Every early-return path emits a `tts_skipped` log so silent drops
        are debuggable. The prior version returned silently on six guards
        (wrong emoji, self-reaction, missing guild/channel, missing message,
        empty text) which made "ya no responde el TTS" regressions invisible.
        """
        if str(payload.emoji) != SPEAK_EMOJI:
            return
        log.info(
            "tts_reaction_received",
            user_id=payload.user_id,
            channel_id=payload.channel_id,
            message_id=payload.message_id,
        )
        if payload.user_id == self.bot.user.id:
            log.debug("tts_skipped", reason="self_reaction", message_id=payload.message_id)
            return

        # Resolve channel directly via the bot cache. Works for guild text
        # channels AND DMs (which have payload.guild_id=None). The old code
        # took a guild-first path — get_guild(None) returned None and the
        # handler silent-dropped every DM reaction. Reported 2026-04-24 by
        # bernard2389: TTS stopped responding because he moved from #general
        # to DM, and nothing ever reached the handler past the guild guard.
        channel = self.bot.get_channel(payload.channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(payload.channel_id)
            except discord.NotFound, discord.Forbidden:
                log.warning(
                    "tts_skipped",
                    reason="channel_not_found",
                    channel_id=payload.channel_id,
                    guild_id=payload.guild_id,
                )
                return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            log.warning("tts_skipped", reason="message_not_found", message_id=payload.message_id)
            return

        # Sibling personas (Vultur…) own their OWN voice via the persona_gateway.
        # Insult must NOT speak for them — doing so renders a sibling's text in
        # Insult's onyx with Insult's typing (the "Vultur TTS sonó como Insult"
        # bug). The gateway's own VoiceClient handles 🔊 on its messages.
        if str(message.author.id) in sibling_bot_user_ids():
            log.info(
                "tts_skipped",
                reason="sibling_persona",
                message_id=payload.message_id,
                author_id=message.author.id,
            )
            return

        text = message.content.strip()
        if not text:
            log.info(
                "tts_skipped",
                reason="empty_content",
                message_id=payload.message_id,
                author_is_bot=message.author.bot,
                attachments=len(message.attachments),
            )
            return

        # Multi-chunk reassembly. delivery.py splits long responses into
        # Discord messages of ≤1990 chars (~2:05 of speech). When a user
        # reacts 🔊 on a bot-authored chunk, look up the full pre-chunk
        # response in memory so TTS doesn't cut off mid-thought.
        original_chunk_len = len(text)
        reassembled = False
        if message.author.id == self.bot.user.id:
            full = await resolve_full_response(self.memory, str(channel.id), message.content)
            if full and full != message.content:
                text = full.strip()
                reassembled = True

        # Pick the voice by message author — ALICE's messages get her female
        # voice, everyone else (Insult, humans) gets onyx. See pick_tts_voice.
        voice, is_alice = pick_tts_voice(message.author.id, self.settings)

        # Generate TTS audio
        try:
            async with channel.typing():
                provider = "azure_openai"
                spoken_voice = voice
                if self.settings.arbor_tts_url:
                    audio_bytes = await generate_arbor_tts_audio(text, self.settings)
                    provider = "arbor_tts"
                    spoken_voice = self.settings.arbor_tts_voice
                else:
                    client = self._get_tts_client()
                    if not client:
                        log.warning("tts_not_configured")
                        return
                    audio_bytes = await synthesize_azure_tts(
                        client,
                        text,
                        voice=voice,
                        deployment=self.settings.azure_openai_tts_deployment,
                    )
                log.info(
                    "tts_generated",
                    text_len=len(text),
                    chunk_len=original_chunk_len,
                    reassembled=reassembled,
                    audio_bytes=len(audio_bytes),
                    voice=spoken_voice,
                    fallback_voice=voice,
                    is_alice=is_alice,
                    provider=provider,
                )
        except Exception:
            log.exception("tts_generation_failed")
            await channel.send("Se me trabo la voz. Intentale otra vez.")
            return

        # Send as audio file attachment
        audio_file = discord.File(io.BytesIO(audio_bytes), filename="personas.insult.mp3")
        await channel.send(file=audio_file)
        # DMChannel has no `.name`; fall back to a safe descriptor.
        channel_label = getattr(channel, "name", None) or f"dm:{channel.id}"
        log.info("tts_sent", text_len=len(text), channel=channel_label)

    @commands.Cog.listener("on_message")
    async def auto_speak_long_reply(self, message: discord.Message) -> None:
        """Auto-TTS: speak Insult's OWN long replies so a wall of text ships a
        voice clip. Azure-only and OFF by default (auto_tts_min_chars=0).

        Fires on the reply's final chunk (the version tag marks it);
        ``resolve_full_response`` reassembles the full pre-chunk text so one
        audio (split into ≤4096 segments) covers the whole reply. Suppressed when
        Arbor is active (voice.md: Arbor stays manual/on-demand)."""
        min_chars = getattr(self.settings, "auto_tts_min_chars", 0)
        if min_chars <= 0 or self.bot.user is None:
            return
        if message.author.id != self.bot.user.id:
            return  # only Insult's own messages
        if not _VERSION_TAG_RE.search(message.content):
            return  # not a reply's final (version-tagged) chunk
        full = await resolve_full_response(self.memory, str(message.channel.id), message.content)
        text = _VERSION_TAG_RE.sub("", full or message.content).strip()
        if not should_auto_tts(text, min_chars=min_chars, arbor_active=bool(self.settings.arbor_tts_url)):
            return
        client = self._get_tts_client()
        if client is None:
            return
        segments = split_for_tts(text)
        try:
            async with message.channel.typing():
                for idx, segment in enumerate(segments):
                    audio_bytes = await synthesize_azure_tts(
                        client,
                        segment,
                        voice=self.settings.tts_voice,
                        deployment=self.settings.azure_openai_tts_deployment,
                    )
                    fname = f"personas.insult{'' if len(segments) == 1 else f'-{idx + 1}'}.mp3"
                    await message.channel.send(file=discord.File(io.BytesIO(audio_bytes), filename=fname))
            log.info("tts_auto_sent", text_len=len(text), segments=len(segments))
        except Exception:
            log.exception("tts_auto_failed")
