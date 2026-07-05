"""Message batching: accumulate rapid-fire messages, dedup, enforce cooldown.

The cog's `on_message` handler hands every raw Discord message to
`BatchManager.handle_incoming`. The manager owns:
  - `_pending`: per-user per-channel accumulation buffer with a scheduled
    flush timer, so fast typists see ONE bot reply to their burst instead
    of N replies.
  - `_processed`: message-id set to suppress duplicate dispatches from
    gateway replays / reconnects.
  - `_last_response_time`: monotonic timestamp per user for MIN_RESPONSE_GAP
    token-protection cooldown.

When a batch is ready, the manager calls `flush_callback(last_message,
combined_text)` — the cog's `_respond`. Voice messages are transcribed
via the injected `transcribe_voice` callable before batching.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import discord
import structlog

from personas.insult.core.errors import ErrorType, get_error_response
from shared.personas.registry import sibling_aliases, sibling_bot_user_ids

log = structlog.get_logger()

MAX_MESSAGE_LENGTH = 4000
BATCH_WAIT_SECONDS = 3.0  # Wait this long after last message before responding
MIN_RESPONSE_GAP = 5.0  # Minimum seconds between bot responses to same user (token protection)

_HOST_NAME_PREFIX = re.compile(r"@?insult\b", re.IGNORECASE)


def _opens_addressing_host(message: discord.Message) -> bool:
    """True when the message OPENS by addressing Insult (the host) by name or
    by its own @mention pill.

    The addressee is whoever HEADS the message: "insult, invita a alice" is a
    request TO Insult that merely names a sibling, not a message FOR the
    sibling. Without this guard the alias scan below muted Insult on every
    explicit ask that names ALICE — so `invoke_alice` could never fire on a
    direct request (msg_skipped_addressed_to_sibling, 2026-07-04 21:50Z).
    """
    content = (message.content or "").lstrip()
    if _HOST_NAME_PREFIX.match(content):
        return True
    me = getattr(getattr(message, "guild", None), "me", None)
    return me is not None and re.match(rf"<@!?{me.id}>", content) is not None


def addressed_to_sibling(message: discord.Message) -> bool:
    """True when this message addresses any registered Khimeras sibling bot — so
    Insult stays silent and lets the sibling (Vultur, ALICE…) answer instead of
    butting in.

    Registry-driven, read at call time — no per-bot hardcoding. Adding a persona
    (`shared/personas/registry.py`) makes Insult suppress for it automatically.
    This is the single suppression gate for ALL siblings; ALICE is no longer a
    special case (her id + aliases live in the registry like every other sibling).

    Three signals, in order of reliability:
    1. **User-mention** — `<@id>` / `message.mentions` resolves to the bot user.
    2. **Role-mention** — Discord autocomplete often inserts the sibling's
       managed role `<@&roleid>` instead; match it via the role whose
       `tags.bot_id` is a registered sibling.
    3. **Text alias** — a whole-word alias the persona opted into in the registry
       (e.g. ALICE's "amix"/"ali"/"alicia"). Default-empty per persona to avoid
       false positives — e.g. "vultur" as a word could fire on film-critic talk.

    Intrusive/clinical keywords are intentionally excluded: those are shared
    context both bots may address; this gate is only "I'm talking to a sibling."

    A message that OPENS addressing Insult is never sibling-addressed, even if
    it names or mentions a sibling later — the head of the message wins.
    """
    if _opens_addressing_host(message):
        return False
    sibling_ids = sibling_bot_user_ids()
    mention_ids = {str(u.id) for u in message.mentions}
    if mention_ids & sibling_ids:
        return True
    if message.guild is not None:
        raw_role_ids = set(re.findall(r"<@&(\d+)>", message.content or ""))
        if raw_role_ids:
            for role in message.guild.roles:
                tags = getattr(role, "tags", None)
                if (
                    tags is not None
                    and str(getattr(tags, "bot_id", "") or "") in sibling_ids
                    and str(role.id) in raw_role_ids
                ):
                    return True

    low = (message.content or "").lower()
    return any(re.search(rf"\b{re.escape(a.lower())}\b", low) for a in sibling_aliases() if a)


@dataclass
class _MessageBatch:
    """Accumulates rapid-fire messages from one user before responding."""

    messages: list[discord.Message] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    timer: asyncio.TimerHandle | None = None


class BatchManager:
    """Holds per-user dedup, cooldown, and batching state."""

    def __init__(self, processed_max: int = 1000):
        self._pending: dict[str, _MessageBatch] = {}
        self._processed: set[int] = set()
        self._processed_max = processed_max
        self._last_response_time: dict[int, float] = {}

    def record_response(self, user_id: int) -> None:
        """Call from `_respond` so MIN_RESPONSE_GAP starts ticking from now."""
        self._last_response_time[user_id] = time.monotonic()

    async def handle_incoming(
        self,
        message: discord.Message,
        *,
        settings,
        memory,
        bot,
        flush_callback: Callable[[discord.Message, str], Awaitable[None]],
        transcribe_voice: Callable[[discord.Message, object], Awaitable[str | None]],
    ) -> None:
        """Apply every filter/gate then either add to batch or short-circuit."""
        # Ignore bots (including ourselves)
        if message.author.bot:
            return

        # Dedup: gateway replays or reconnect storms
        if message.id in self._processed:
            log.debug("msg_dropped_duplicate", message_id=message.id, user_id=message.author.id)
            return
        self._processed.add(message.id)
        if len(self._processed) > self._processed_max:
            to_keep = sorted(self._processed)[self._processed_max // 2 :]
            self._processed = set(to_keep)

        # Ignore !ping, !memoria, etc. — handled by other cogs as commands
        if message.content.startswith(settings.command_prefix):
            return

        # Directly addressed to a Khimeras sibling (Vultur, ALICE…) → Insult
        # stays silent and lets the right bot answer. We STILL PERSIST the message
        # so the shared `messages` table keeps full context for all bots (Insult
        # is the canonical storage gateway; skipping storage would blind siblings).
        if addressed_to_sibling(message):
            log.info(
                "msg_skipped_addressed_to_sibling",
                sibling="persona_sibling",
                message_id=message.id,
                user_id=message.author.id,
                channel_id=message.channel.id,
            )
            stored_text = message.content.strip()
            if stored_text:
                try:
                    await memory.store(
                        str(message.channel.id),
                        str(message.author.id),
                        message.author.display_name,
                        "user",
                        stored_text,
                        guild_id=str(message.guild.id) if message.guild else None,
                        channel_name=message.channel.name if hasattr(message.channel, "name") else None,
                        discord_message_id=str(message.id),
                    )
                except Exception:
                    log.exception("chat_store_sibling_addressed_failed")
            return

        # Voice transcription
        text = message.content.strip()
        if message.flags.voice and message.attachments:
            text = await transcribe_voice(message, settings) or ""
            # Echo the transcription to the channel so non-listeners (and
            # future log readers) can see what was said. Discord voice
            # messages are otherwise opaque unless you hit play. We use
            # channel.send directly (not send_response) so no version tag
            # or [SEND]-chunking is applied — this is a sidecar, not a
            # bot turn of its own.
            if text:
                try:
                    # Discord block-quote (`>>>` — multi-line) gives the echo
                    # a vertical bar in the client so readers can visually
                    # separate "what the user said" from the bot's reply,
                    # which arrives as a normal message right after.
                    echo = f">>> 🔊 **{message.author.display_name} dijo:**\n{text}\n🎙️"
                    # Discord hard limit is 2000 chars per message; truncate
                    # with an ellipsis if Whisper produced a novel.
                    if len(echo) > 1990:
                        echo = echo[:1987] + "…"
                    await message.channel.send(echo)
                except Exception:
                    log.exception("voice_transcription_echo_failed")

        # Empty message (sticker-only, reaction-only, etc.)
        if not text and not message.attachments:
            log.debug(
                "msg_dropped_empty",
                message_id=message.id,
                user_id=message.author.id,
                attachments=len(message.attachments),
            )
            return

        # Reset proactive backoff: a user just spoke
        if hasattr(bot, "_reset_proactive_backoff"):
            bot._reset_proactive_backoff()

        # Too long
        if len(text) > MAX_MESSAGE_LENGTH:
            log.info(
                "msg_dropped_too_long",
                message_id=message.id,
                user_id=message.author.id,
                text_len=len(text),
                limit=MAX_MESSAGE_LENGTH,
            )
            await message.channel.send(get_error_response(ErrorType.TOO_LONG))
            return

        # Per-user cooldown: don't burn tokens on rapid-fire replies
        now = time.monotonic()
        last = self._last_response_time.get(message.author.id, 0)
        if now - last < MIN_RESPONSE_GAP:
            log.info(
                "msg_dropped_cooldown",
                message_id=message.id,
                user_id=message.author.id,
                channel_id=message.channel.id,
                since_last_response_s=round(now - last, 2),
                min_gap_s=MIN_RESPONSE_GAP,
            )
            # Still accumulate in memory — don't lose context
            try:
                await memory.store(
                    str(message.channel.id),
                    str(message.author.id),
                    message.author.display_name,
                    "user",
                    text,
                    guild_id=str(message.guild.id) if message.guild else None,
                    channel_name=message.channel.name if hasattr(message.channel, "name") else None,
                    discord_message_id=str(message.id),
                )
            except Exception:
                log.exception("chat_store_cooldown_failed")
            return

        # Accumulate into the per-user batch
        batch_key = f"{message.channel.id}:{message.author.id}"
        batch = self._pending.get(batch_key)
        if batch is None:
            batch = _MessageBatch()
            self._pending[batch_key] = batch
        batch.messages.append(message)
        batch.texts.append(text)

        # Cancel the previous timer so the clock resets with each new message
        if batch.timer is not None:
            batch.timer.cancel()

        log.debug(
            "msg_batched",
            batch_key=batch_key,
            batch_size=len(batch.messages),
            text_len=len(text),
        )

        loop = asyncio.get_running_loop()
        batch.timer = loop.call_later(
            BATCH_WAIT_SECONDS,
            lambda k=batch_key: asyncio.create_task(self._flush(k, flush_callback)),
        )

    async def _flush(
        self,
        batch_key: str,
        flush_callback: Callable[[discord.Message, str], Awaitable[None]],
    ) -> None:
        """Pop the batch and dispatch to `_respond` with combined text."""
        batch = self._pending.pop(batch_key, None)
        if not batch or not batch.messages:
            log.debug("batch_flush_empty", batch_key=batch_key)
            return

        last_message = batch.messages[-1]
        combined_text = "\n".join(batch.texts)

        log.debug(
            "batch_flush_start",
            batch_key=batch_key,
            batch_size=len(batch.messages),
            combined_len=len(combined_text),
        )

        await flush_callback(last_message, combined_text)
