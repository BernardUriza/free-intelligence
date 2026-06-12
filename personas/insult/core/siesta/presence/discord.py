"""Discord presence updates driven by siesta phase transitions.

When the bot is asleep we surface that NATIVELY in the Discord member
list — no need to send a chat message and burn a token. The user sees
a 🌙 idle indicator next to the bot's avatar with a custom-status line
like "🛌 soñando — usuario 1/2 (47%)".

This module is the only place where ``bot.change_presence`` is called
for siesta state, so the icon-and-string convention lives in one spot
and is unit-testable via ``build_activity_text``.

The ``SiestaPresenceUpdater`` is hooked into the
:class:`~insult.core.siesta.coordination.poller.SiestaPoller` as a
listener: every time the poller observes a phase transition, the
updater renders the new presence and pushes it to Discord. Within a
phase, progress ticks are NOT pushed (they'd burn rate limits — Discord
caps presence updates at ~5/min) — only on phase change.
"""

from __future__ import annotations

import discord
import structlog

from personas.insult.core.siesta.state import SiestaPhase, SiestaSnapshot

log = structlog.get_logger()

_PHASE_LABEL: dict[SiestaPhase, str] = {
    SiestaPhase.LIGHT: "echandome la siesta",
    SiestaPhase.DEEP: "soñando profundo",
    SiestaPhase.REM: "soñando — escribiendo el diario",
    SiestaPhase.AWAKE: "",
}


def build_activity_text(snapshot: SiestaSnapshot) -> str:
    """Render the custom-status string for a snapshot. Pure, testable.

    Returns empty string for AWAKE (caller should clear the activity).
    Format keeps under Discord's 128-char custom status cap.
    """
    if not snapshot.is_active:
        return ""
    label = _PHASE_LABEL.get(snapshot.phase, "siesta")
    if snapshot.total_users > 0:
        return f"🛌 {label} — {snapshot.processed_users}/{snapshot.total_users} ({snapshot.progress_pct}%)"
    return f"🛌 {label}"


def status_for(snapshot: SiestaSnapshot) -> discord.Status:
    """Map a snapshot to a Discord presence status enum."""
    return discord.Status.idle if snapshot.is_active else discord.Status.online


class SiestaPresenceUpdater:
    """Listener bound to a SiestaPoller — pushes presence on phase change."""

    def __init__(self, bot: discord.Client) -> None:
        self._bot = bot

    async def __call__(self, _previous: SiestaSnapshot, current: SiestaSnapshot) -> None:
        """Poller-listener signature: (previous, current) -> awaitable."""
        await self.apply(current)

    async def apply(self, snapshot: SiestaSnapshot) -> None:
        """Push the snapshot to Discord. Errors logged, never raised."""
        text = build_activity_text(snapshot)
        activity = discord.CustomActivity(name=text) if text else None
        try:
            await self._bot.change_presence(status=status_for(snapshot), activity=activity)
            log.info("siesta_presence_updated", phase=snapshot.phase.value, text=text)
        except Exception:
            log.exception("siesta_presence_update_failed")
