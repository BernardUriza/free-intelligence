"""The host dispatch loop — the behaviour of the omnipresent receiver (#6, slice 3).

Ties the two cores together: inbound messages feed the batcher
(`demux_ai.batch`); a periodic tick pops the debounced batches and routes each to
a persona (`demux_ai.dispatch`). This is ALL of the host's logic — deliberately
separated from the `discord.Client` shell so it is unit-testable with a fake clock
and a mocked router, no token, no gateway connection. The Discord shell (on_message
→ handle_message, a tasks.loop → tick, start(token)) is thin glue over this and is
the only part that needs the host's Discord token (Bernard's cutover atom).

Reception model (decision (a), from Bernard's documented direction): the host sees
EVERY human message and decides who answers — Insult included, now just a routing
target. Bot-authored messages and command-prefixed lines are ignored so the host
never routes another bot's output or a `!command`.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

from demux_ai.batch import MessageBatcher
from demux_ai.dispatch import route_and_dispatch
from shared.personas.registry import persona_id_by_role_name

log = structlog.get_logger()

COMMAND_PREFIXES = ("!", "/")

# How many recent channel messages ride to the routing brain as context. Mirrors
# the dead `_fetch_router_context` (personas/insult/cogs/chat/stages.py, killed in
# 2f8d9ad) and `scripts/router_eval.py::ROUTER_CONTEXT_MESSAGES` — the eval measures
# the router against THIS number, so they move together or the eval measures another
# system.
CONTEXT_MESSAGES = 8
CONTEXT_LINE_CHARS = 300


@dataclass
class HostDispatchLoop:
    """Owns the batcher + router; turns a stream of messages into routed turns."""

    router: object
    batcher: MessageBatcher = field(default_factory=MessageBatcher)
    mention_targets: dict[str, str] = field(default_factory=dict)
    role_resolver: Callable[[str], str | None] = persona_id_by_role_name
    # How a chosen persona is summoned. None = the bare fire-and-forget
    # `summon_persona`; the live host injects `HostClient.dispatch_with_fallback`,
    # which waits for the turn in the background and owns its failure.
    dispatcher: Callable[..., Awaitable[Any]] | None = None
    _names: dict[str, str] = field(default_factory=dict)
    _forced_targets: dict[str, list[str]] = field(default_factory=dict)
    _context: dict[str, deque[str]] = field(default_factory=dict)
    _last_target: dict[str, str] = field(default_factory=dict)

    def remember(self, *, channel_id: str, author_name: str, text: str) -> None:
        """Keep the last `CONTEXT_MESSAGES` lines of a channel for the routing brain.

        Called for EVERY message, personas included — a persona's reply is half of
        what makes the next message a continuation, and `handle_message` drops bot
        authors before anything is retained. Format is the canonical
        `name: text[:300]`, oldest first, byte-identical to the deleted
        `_fetch_router_context` and to `scripts/router_eval.py`, so the eval and
        production measure the same system.

        `author_name` must be the persona's REGISTRY display name, never
        `discord.Member.display_name`: the latter returns the per-guild nickname
        ("frugi") while `host_routing.md` maps only the canonical one ("Frugívoro").
        A nickname in the context block is a name the brain cannot resolve.

        In-memory on purpose: the host has no `POSTGRES_URL`, and it does not need
        one — every message already passes through `on_message`.
        """
        line = text.strip()
        if not line:
            return
        buffer = self._context.setdefault(channel_id, deque(maxlen=CONTEXT_MESSAGES))
        buffer.append(f"{author_name or '?'}: {line[:CONTEXT_LINE_CHARS]}")

    def context_for(self, channel_id: str) -> str | None:
        """The recent-conversation block for `channel_id`, or None when empty.

        None (not "") is the contract `route_and_dispatch` expects: it means route
        WITHOUT context, which keeps the payload byte-identical to the pre-context
        router instead of shipping an empty header.
        """
        buffer = self._context.get(channel_id)
        return "\n".join(buffer) if buffer else None

    def handle_message(
        self,
        *,
        channel_id: str,
        author_id: str,
        author_is_bot: bool,
        text: str,
        now: float,
        author_name: str = "",
        message_id: str | None = None,
        mentioned_ids: list[str] | None = None,
        mentioned_role_names: list[str] | None = None,
        attachment_names: list[str] | None = None,
        voice_text: str = "",
    ) -> bool:
        """Feed one inbound message to the batcher. Returns True if accepted.

        Ignored (returns False, nothing batched): a bot author (never route another
        bot's output — the Insult↔Vultur loop guard applies to the host too) and a
        command-prefixed line (`!`/`/` are commands, not turns).

        `message_id` rides through the batcher so the routed turn's [REACT:] markers
        can anchor to the last message of the burst (else host-routed reactions drop).
        When a burst contains explicit persona user/role @mentions, EVERY mentioned
        registered persona is summoned (in mention order, deduped) and the LLM
        router is bypassed at dispatch time.

        `attachment_names` makes bare images ROUTABLE (2026-07-16 bug: una imagen
        pelona era text="" → el batcher la tiraba y nadie respondía jamás). The
        attachment becomes a visible note in the batched text — the router reads
        "[adjuntó: foto.png]" and routes — and the batcher prefers the
        attachment-bearing message as the burst's trigger, so the routed persona
        actually FETCHES the image (the invite path harvests attachments from the
        trigger message).

        `voice_text` is the receiver's transcript of that message's voice notes.
        It becomes the message's ROUTABLE text, because the filename note alone
        made the router pick a persona without knowing what was said
        (2026-07-23) — "[adjuntó: voice-message.ogg]" says nothing about whether
        the audio is about cinema, a health scare or a landlord. The filename
        note still rides along so the trigger keeps preferring this message.
        """
        if author_is_bot:
            return False
        stripped = text.strip()
        if stripped.startswith(COMMAND_PREFIXES):
            return False
        key = f"{channel_id}:{author_id}"
        names = [n for n in (attachment_names or []) if n]
        spoken = voice_text.strip()
        if spoken:
            stripped = f"{stripped}\n{spoken}" if stripped else spoken
        if names:
            note = f"[adjuntó: {', '.join(names)}]"
            batched_text = f"{stripped}\n{note}" if stripped else note
        else:
            batched_text = stripped or text
        self.batcher.add(
            key,
            batched_text,
            now,
            message_id,
            has_attachments=bool(names),
            voice_transcript=spoken,
        )
        if author_name:
            self._names[key] = author_name
        # Within ONE message every mention counts ("@Vultur @Insult @frugi
        # @A.L.I.C.E. cuéntenme cada quien" wakes four). ACROSS the burst the
        # newest mentioning message REPLACES the previous set, because a second
        # message that names someone else is a correction ("@ALICE mejor tú"),
        # not an addition.
        forced: list[str] = []
        for target in [self.mention_targets.get(m) for m in mentioned_ids or []] + [
            self.role_resolver(r) for r in mentioned_role_names or []
        ]:
            if target and target not in forced:
                forced.append(target)
        if forced:
            self._forced_targets[key] = forced
        return True

    async def tick(self, now: float) -> list:
        """Flush every due batch and dispatch it. Returns the routing decisions
        (for telemetry/tests). One batch's dispatch fault never blocks the others.

        `prev_target` viaja SOLO como telemetría: mide continuidad, no la impone.
        La afinidad de sesión de verdad (stay bias / idle timeout) es una decisión
        de diseño aparte; esto es lo que permite medirla ANTES de decidirla.
        """
        decisions = []
        for key, combined, message_id, voice_transcript in self.batcher.pop_due(now):
            channel_id = key.split(":", 1)[0]
            decision = await route_and_dispatch(
                self.router,
                channel_id=channel_id,
                text=combined,
                user_name=self._names.pop(key, ""),
                context=self.context_for(channel_id),
                trigger_message_id=message_id,
                forced_targets=self._forced_targets.pop(key, None),
                voice_transcript=voice_transcript,
                prev_target=self._last_target.get(channel_id),
                dispatcher=self.dispatcher,
            )
            decisions.append(decision)
            landed = getattr(decision, "target", None)
            if landed:
                self._last_target[channel_id] = landed
        return decisions
