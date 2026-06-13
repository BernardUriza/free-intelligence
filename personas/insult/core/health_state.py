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
        self._serving: bool = False

    # ---------- write ----------

    def set_bot(self, bot: Any) -> None:
        """Wire the discord.py Bot reference so ``is_bot_ready`` and
        ``gateway_latency_ms`` can answer. Called at the TOP of
        ``on_ready``, BEFORE the message pipeline (cogs/``on_message``) is
        attached — so ``is_bot_ready`` going True does NOT mean the bot can
        serve. ``mark_serving`` is the signal for that."""
        self._bot_ref = bot

    def mark_serving(self) -> None:
        """Mark that ``on_ready`` finished wiring the bot end-to-end (cogs
        added, listeners attached, background loops started). This is the
        only signal that distinguishes "Discord gateway ready event fired"
        from "the bot can actually process a message". Set at the END of
        ``on_ready``; sticky-true across reconnects (cogs persist).

        Exists because on 2026-06-13 a replica hung mid-``on_ready`` AFTER
        ``set_bot`` but BEFORE the cogs were attached: ``/debug/health``
        read ``is_ready=true`` + ``gateway_latency_ms=15.1`` + ``pg ok``
        while the bot silently ate every message. ``is_ready`` was a false
        positive; ``serving`` would have been False."""
        self._serving = True

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

    def is_serving(self) -> bool:
        """True once ``on_ready`` finished wiring the message pipeline.
        False during the boot window between ``set_bot`` and the end of
        ``on_ready`` — exactly the window where ``is_bot_ready`` can lie."""
        return self._serving

    def guild_count(self) -> int | None:
        """Number of guilds the bot is in, or ``None`` when the bot ref
        isn't wired yet. A live bot is in ≥1 guild; ``0`` with
        ``is_ready=true`` is a half-open gateway (zombie), not a healthy
        idle bot."""
        if self._bot_ref is None:
            return None
        guilds = getattr(self._bot_ref, "guilds", None)
        if guilds is None:
            return None
        try:
            return len(guilds)
        except TypeError:
            return None

    def is_healthy(self) -> bool:
        """Single honest verdict combining every readiness signal, so a
        reader (human or synthetic monitor) cannot cherry-pick one green
        field. True iff: Discord ready event fired AND the message pipeline
        is wired (``serving``) AND the bot is in ≥1 guild AND the gateway
        heartbeat is a real number.

        This is the field to trust over ``is_ready`` alone — the latter was
        the false positive that masked the 2026-06-13 boot-hang outage."""
        return bool(
            self.is_bot_ready()
            and self._serving
            and (self.guild_count() or 0) > 0
            and self.gateway_latency_ms() is not None
        )

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
