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
from shared.personas.registry import sibling_bot_user_ids

log = structlog.get_logger()

MAX_MESSAGE_LENGTH = 4000
BATCH_WAIT_SECONDS = 3.0  # Wait this long after last message before responding
MIN_RESPONSE_GAP = 5.0  # Minimum seconds between bot responses to same user (token protection)


def addressed_to_alice(message: discord.Message, settings) -> bool:
    """True when this message DIRECTLY addresses ALICE — so Insult should stay
    silent and let her answer (no double-reply).

    Mirrors ALICE's own direct-address triggers (alice/cogs/chat.py) so the two
    bots stay in lockstep: every signal that makes ALICE respond also makes
    Insult suppress, which means suppression never produces dead air. Three
    signals, in order of reliability:

    1. **User-mention** — the ``@A.L.I.C.E.`` pill resolves to ``<@id>`` /
       ``<@!id>`` in content (and to ``message.mentions``).
    2. **Role-mention** — Discord's autocomplete often inserts ALICE's managed
       role ``<@&roleid>`` instead of the user pill; match it via the role whose
       ``tags.bot_id`` is ALICE (same trick ALICE uses for inbound).
    3. **Text alias** — plain-text ``@alice`` / ``alice`` / ``amix`` / ``ali`` /
       ``alicia`` as a whole word.

    Intrusive clinical keywords are intentionally excluded: those are shared
    context both bots may address; this gate is only "I'm talking to ALICE."
    """
    aid = (getattr(settings, "alice_bot_user_id", "") or "").strip()
    content = message.content or ""

    if aid:
        if aid in {str(u.id) for u in message.mentions}:
            return True
        if re.search(rf"<@!?{re.escape(aid)}>", content):
            return True
        if message.guild is not None:
            raw_role_ids = set(re.findall(r"<@&(\d+)>", content))
            if raw_role_ids:
                for role in message.guild.roles:
                    tags = getattr(role, "tags", None)
                    if (
                        tags is not None
                        and str(getattr(tags, "bot_id", "") or "") == aid
                        and str(role.id) in raw_role_ids
                    ):
                        return True

    low = content.lower()
    aliases = [*getattr(settings, "alice_aliases", []), "alice"]
    return any(re.search(rf"\b{re.escape(a.lower())}\b", low) for a in aliases if a)


def addressed_to_sibling(message: discord.Message) -> bool:
    """True when this message addresses any registered Khimeras sibling bot — so
    Insult stays silent and lets the sibling (e.g. Vultur) answer instead of
    butting in.

    Reads `shared/personas/registry.py` at call time — no config coupling. When
    a new persona is added to the registry, Insult automatically suppresses for
    it without any change here. Works alongside `addressed_to_alice` (which
    handles ALICE specifically, including text aliases).

    Matches BOTH addressing forms, because the persona_gateway summons a sibling
    on its OWN role mention (v4.21.91), not only the user pill:
    1. **User-mention** — `<@id>` / `message.mentions` resolves to the bot user.
    2. **Role-mention** — Discord autocomplete often inserts the sibling's
       managed role `<@&roleid>` instead; match it via the role whose
       `tags.bot_id` is a registered sibling (same trick as `addressed_to_alice`).

    Text aliases per sibling stay opt-in in the registry (default empty) to avoid
    false positives — e.g. "vultur" as a word could fire on film-critic talk.
    """
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
    return False


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

        # Directly addressed to ALICE or any Khimeras sibling → Insult stays
        # silent and lets the right bot answer. We STILL PERSIST the message so
        # the shared `messages` table keeps full context for all bots (Insult is
        # the canonical storage gateway; skipping storage would blind ALICE/Vultur).
        _to_alice = addressed_to_alice(message, settings)
        _to_sibling = addressed_to_sibling(message)
        if _to_alice or _to_sibling:
            sibling_label = "alice" if _to_alice else "persona_sibling"
            log.info(
                "msg_skipped_addressed_to_sibling",
                sibling=sibling_label,
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
