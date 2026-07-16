"""The Discord shell of the omnipresent host (#6, slice 4 — code-complete).

Thin glue over the tested `HostDispatchLoop`: `on_message` ingests every message
into the loop's batcher, a 1s `tasks.loop` flushes due batches and dispatches them.
The host is the ONLY omnipresent listener once it's live (Insult demotes to a
routed persona at cutover) — so it reads all message content and routes each burst
to whoever the router picks.

Split on purpose: the field-mapping (`_ingest`) is pure and unit-tested; the
`discord.Client` lifecycle (`start(token)`, the loop scheduler) is declared glue
whose only untestable part is the literal network connection — which needs the
host's Discord token, Bernard's cutover atom. `run_host` refuses to start without
one, so the shell is dormant (no double-omnipresent conflict) until he flips it on.
"""

from __future__ import annotations

import os
import time

import discord
import structlog
from discord.ext import tasks

from demux_ai.host_loop import HostDispatchLoop
from shared.personas.registry import persona_id_by_bot_user_id

log = structlog.get_logger()

HOST_TOKEN_ENV = "HOST_DISCORD_TOKEN"  # noqa: S105 # nosec B105 — env-var NAME, not a secret
TICK_SECONDS = 1.0


class HostClient(discord.Client):
    """Omnipresent receiver: every message → the dispatch loop's batcher."""

    def __init__(self, dispatch_loop: HostDispatchLoop, *, intents: discord.Intents) -> None:
        super().__init__(intents=intents)
        self.dispatch_loop = dispatch_loop

    def _ingest(self, message: discord.Message, now: float) -> bool:
        """Map a Discord message onto the loop and batch it. Pure over the loop —
        returns whether it was accepted (a human, non-command message)."""
        mentioned_ids = [str(user.id) for user in getattr(message, "mentions", [])]
        return self.dispatch_loop.handle_message(
            channel_id=str(message.channel.id),
            author_id=str(message.author.id),
            author_is_bot=bool(message.author.bot),
            text=message.content or "",
            now=now,
            author_name=getattr(message.author, "display_name", ""),
            message_id=str(message.id),
            mentioned_ids=mentioned_ids,
        )

    async def on_ready(self) -> None:
        log.info("host_ready", bot_id=self.user.id if self.user else None)
        if not self._tick.is_running():
            self._tick.start()

    async def on_message(self, message: discord.Message) -> None:
        self._ingest(message, time.time())

    @tasks.loop(seconds=TICK_SECONDS)
    async def _tick(self) -> None:
        try:
            await self.dispatch_loop.tick(time.time())
        except Exception:
            log.exception("host_tick_failed")


def build_host(router: object) -> HostClient:
    """Wire a HostClient with message-content intent (needed to read text)."""
    intents = discord.Intents.default()
    intents.message_content = True
    return HostClient(
        HostDispatchLoop(router=router, mention_targets=persona_id_by_bot_user_id()),
        intents=intents,
    )


def run_host(router: object, token: str | None = None) -> None:
    """Start the host bot. Refuses (logs + returns) without a token — the shell is
    dormant until the cutover atom is provided, so it never becomes a second
    omnipresent bot fighting Insult for reception."""
    token = token or os.environ.get(HOST_TOKEN_ENV, "")
    if not token:
        log.error("host_no_token", env=HOST_TOKEN_ENV)
        return
    build_host(router).run(token)
