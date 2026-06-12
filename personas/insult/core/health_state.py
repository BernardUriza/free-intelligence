"""Process-wide health state for liveness/readiness probes.

Tracks signals that ``/debug/health`` reports out, so a black-box
synthetic monitor (KQL alert, GitHub Action probe, Azure Container
Apps health probe) can answer three different questions cheaply:

- **Liveness** — is the Python process up at all? Answered by the
  endpoint responding 200 at all.
- **Readiness** — is the bot connected to Discord and processing
  events? Answered by ``is_ready`` + ``gateway_latency_ms``.
- **Bot-responsive** — has the bot actually finished a chat turn
  recently? Answered by ``last_turn_age_s``.

The third one is the load-bearing addition. Pre-PR1, a Discord bot
could be ``is_ready=True`` with a healthy gateway latency while
``on_message`` had silently stopped processing turns (zombie
handler) — the same failure mode that produced the 2026-05-08T23:59
outage. ``last_turn_age_s`` is the only signal that distinguishes
"bot alive" from "bot processing".

Singleton intentionally — the bot is one process per replica. Multiple
``HealthState`` instances would split the truth and the synthetic
monitor would see whichever instance happens to be wired to the HTTP
handler. Module-level singleton avoids that whole class of bug.

Reset on process restart, by design — restart means the bot has no
recent turn data anyway, and "I just started, I haven't done a turn
yet" is correctly reflected as ``last_turn_age_s = None``.
"""

from __future__ import annotations

import time
from typing import Any


class HealthState:
    """In-memory health signals for a single bot process."""

    def __init__(self) -> None:
        self._last_turn_at: float | None = None  # monotonic seconds
        self._last_turn_outcome: str | None = None
        self._bot_ref: Any = None
        self._started_at: float = time.monotonic()
        self._turns_total: int = 0

    # ---------- write ----------

    def set_bot(self, bot: Any) -> None:
        """Wire the discord.py Bot reference so ``is_bot_ready`` and
        ``gateway_latency_ms`` can answer. Called once during boot
        after the Bot is constructed."""
        self._bot_ref = bot

    def record_turn_end(self, outcome: str = "ok") -> None:
        """Mark that ``cog.py`` just emitted a ``chat_turn_end``.
        ``outcome`` mirrors the value logged on that event so a future
        observability layer can break down "fresh turns" by outcome
        class without re-parsing logs."""
        self._last_turn_at = time.monotonic()
        self._last_turn_outcome = outcome
        self._turns_total += 1

    # ---------- read ----------

    def last_turn_age_s(self) -> float | None:
        """Seconds since the last ``record_turn_end``. ``None`` until
        the first turn has completed in this process lifetime."""
        if self._last_turn_at is None:
            return None
        return time.monotonic() - self._last_turn_at

    def last_turn_within(self, seconds: float) -> bool:
        """True iff a turn completed in the last ``seconds``. False
        also covers the cold-start case (no turn ever)."""
        age = self.last_turn_age_s()
        return age is not None and age <= seconds

    def last_turn_outcome(self) -> str | None:
        return self._last_turn_outcome

    def is_bot_ready(self) -> bool | None:
        """``None`` when the bot ref hasn't been wired yet (boot
        racing the probe); otherwise ``bool(bot.is_ready())``."""
        if self._bot_ref is None:
            return None
        is_ready = getattr(self._bot_ref, "is_ready", None)
        if callable(is_ready):
            return bool(is_ready())
        return None

    def gateway_latency_ms(self) -> float | None:
        """Discord WebSocket heartbeat latency in milliseconds, or
        ``None`` when the bot ref isn't wired or latency isn't yet
        measured (``float('nan')`` from discord.py before first
        heartbeat — we collapse that to ``None``)."""
        if self._bot_ref is None:
            return None
        latency = getattr(self._bot_ref, "latency", None)
        if not isinstance(latency, int | float):
            return None
        if latency != latency:  # NaN — not yet measured
            return None
        return round(latency * 1000.0, 1)

    def uptime_s(self) -> float:
        return time.monotonic() - self._started_at

    def turns_total(self) -> int:
        return self._turns_total


# Process-wide singleton. Importers always see the same instance.
_state = HealthState()


def get_state() -> HealthState:
    return _state


# Test-only seam: replace the singleton's internal state. NOT exported
# for production use — callers should depend on ``record_turn_end`` and
# ``set_bot`` to mutate state.
def _reset_for_tests() -> None:
    global _state
    _state = HealthState()
