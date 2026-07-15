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

from dataclasses import dataclass, field

import structlog

from demux_ai.batch import MessageBatcher
from demux_ai.dispatch import route_and_dispatch

log = structlog.get_logger()

COMMAND_PREFIXES = ("!", "/")


@dataclass
class HostDispatchLoop:
    """Owns the batcher + router; turns a stream of messages into routed turns."""

    router: object
    batcher: MessageBatcher = field(default_factory=MessageBatcher)
    _names: dict[str, str] = field(default_factory=dict)

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
    ) -> bool:
        """Feed one inbound message to the batcher. Returns True if accepted.

        Ignored (returns False, nothing batched): a bot author (never route another
        bot's output — the Insult↔Vultur loop guard applies to the host too) and a
        command-prefixed line (`!`/`/` are commands, not turns).

        `message_id` rides through the batcher so the routed turn's [REACT:] markers
        can anchor to the last message of the burst (else host-routed reactions drop).
        """
        if author_is_bot:
            return False
        stripped = text.strip()
        if stripped.startswith(COMMAND_PREFIXES):
            return False
        key = f"{channel_id}:{author_id}"
        self.batcher.add(key, text, now, message_id)
        if author_name:
            self._names[key] = author_name
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
            )
            decisions.append(decision)
        return decisions
