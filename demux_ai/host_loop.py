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

from collections.abc import Callable
from dataclasses import dataclass, field

import structlog

from demux_ai.batch import MessageBatcher
from demux_ai.dispatch import route_and_dispatch
from shared.personas.registry import persona_id_by_role_name

log = structlog.get_logger()

COMMAND_PREFIXES = ("!", "/")


@dataclass
class HostDispatchLoop:
    """Owns the batcher + router; turns a stream of messages into routed turns."""

    router: object
    batcher: MessageBatcher = field(default_factory=MessageBatcher)
    mention_targets: dict[str, str] = field(default_factory=dict)
    role_resolver: Callable[[str], str | None] = persona_id_by_role_name
    _names: dict[str, str] = field(default_factory=dict)
    _forced_target: dict[str, str] = field(default_factory=dict)

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
    ) -> bool:
        """Feed one inbound message to the batcher. Returns True if accepted.

        Ignored (returns False, nothing batched): a bot author (never route another
        bot's output — the Insult↔Vultur loop guard applies to the host too) and a
        command-prefixed line (`!`/`/` are commands, not turns).

        `message_id` rides through the batcher so the routed turn's [REACT:] markers
        can anchor to the last message of the burst (else host-routed reactions drop).
        When a burst contains explicit persona user/role @mentions, the latest
        mentioned registered persona wins and bypasses the LLM router at dispatch
        time.

        `attachment_names` makes bare images ROUTABLE (2026-07-16 bug: una imagen
        pelona era text="" → el batcher la tiraba y nadie respondía jamás). The
        attachment becomes a visible note in the batched text — the router reads
        "[adjuntó: foto.png]" and routes — and the batcher prefers the
        attachment-bearing message as the burst's trigger, so the routed persona
        actually FETCHES the image (the invite path harvests attachments from the
        trigger message).
        """
        if author_is_bot:
            return False
        stripped = text.strip()
        if stripped.startswith(COMMAND_PREFIXES):
            return False
        key = f"{channel_id}:{author_id}"
        names = [n for n in (attachment_names or []) if n]
        if names:
            note = f"[adjuntó: {', '.join(names)}]"
            batched_text = f"{stripped}\n{note}" if stripped else note
        else:
            batched_text = text
        self.batcher.add(key, batched_text, now, message_id, has_attachments=bool(names))
        if author_name:
            self._names[key] = author_name
        for mentioned_id in mentioned_ids or []:
            target = self.mention_targets.get(mentioned_id)
            if target:
                self._forced_target[key] = target
        for role_name in mentioned_role_names or []:
            target = self.role_resolver(role_name)
            if target:
                self._forced_target[key] = target
        return True

    async def tick(self, now: float) -> list:
        """Flush every due batch and dispatch it. Returns the routing decisions
        (for telemetry/tests). One batch's dispatch fault never blocks the others."""
        decisions = []
        for key, combined, message_id in self.batcher.pop_due(now):
            channel_id = key.split(":", 1)[0]
            decision = await route_and_dispatch(
                self.router,
                channel_id=channel_id,
                text=combined,
                user_name=self._names.pop(key, ""),
                trigger_message_id=message_id,
                forced_target=self._forced_target.pop(key, None),
            )
            decisions.append(decision)
        return decisions
