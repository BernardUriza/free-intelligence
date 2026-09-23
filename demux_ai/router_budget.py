"""Weekly spend cap for the gpt-4.1 host router (HOST 5/6 — implicit routing).

Bernard authorized the LLM router with a hard budget of $5/week (2026-06-21). This
is the in-process enforcement of that constraint: a per-ISO-week running USD total
that fails the router SAFE (back to the deterministic rule) once the cap is hit,
instead of trusting "it's cheap" (an honored constraint, not a fake-green).

In-process is correct here: ``khimeras-host`` runs single-replica (min=max=1), so one
event-loop owns the counter and there is no cross-replica split. ``record`` is sync
(no await) so it is atomic within the asyncio loop. The counter resets on container
restart — acceptable as a RUNAWAY backstop because the only way to reach $5 at the
direct transport's ~115 tokens/call is ~18k calls/week (orders of magnitude over the
bot's real traffic), so a real overspend can only come from a loop/bloat regression,
which trips FAST within a single container lifetime. Every call logs cumulative spend
so the real weekly figure is observable in Log Analytics; if traffic ever grows to
where the cap could bind across restarts, promote the counter to Postgres.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime

import structlog

log = structlog.get_logger()

# Azure OpenAI gpt-4.1 list price (USD per 1M tokens), overridable via env so a
# price change is config, not a code edit. Conservative defaults (standard tier).
_DEFAULT_INPUT_PER_MTOK = 2.00
_DEFAULT_OUTPUT_PER_MTOK = 8.00
_DEFAULT_WEEKLY_CAP_USD = 5.00


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _week_key(dt: datetime) -> tuple[int, int]:
    """ISO (year, week) — the reset boundary. Monday-anchored per ISO-8601."""
    iso = dt.isocalendar()
    return (iso[0], iso[1])


class RouterBudget:
    """A per-ISO-week USD spend cap for the gpt-4.1 router.

    ``can_spend()`` is checked BEFORE a routing call; ``record()`` is called AFTER
    with the call's real token usage. Crossing the cap flips the router off for the
    rest of the week (fail-safe to the deterministic rule). The week rolls over
    automatically when ``_now()`` lands in a new ISO week.
    """

    def __init__(
        self,
        *,
        weekly_cap_usd: float | None = None,
        input_per_mtok: float | None = None,
        output_per_mtok: float | None = None,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._cap = (
            weekly_cap_usd
            if weekly_cap_usd is not None
            else float(os.environ.get("ROUTER_WEEKLY_BUDGET_USD", _DEFAULT_WEEKLY_CAP_USD))
        )
        self._in_rate = (
            input_per_mtok
            if input_per_mtok is not None
            else float(os.environ.get("ROUTER_INPUT_PER_MTOK", _DEFAULT_INPUT_PER_MTOK))
        )
        self._out_rate = (
            output_per_mtok
            if output_per_mtok is not None
            else float(os.environ.get("ROUTER_OUTPUT_PER_MTOK", _DEFAULT_OUTPUT_PER_MTOK))
        )
        self._now = now
        self._week: tuple[int, int] | None = None
        self._spent_usd = 0.0

    def cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        """USD cost of a single call from its token usage."""
        return (input_tokens / 1_000_000) * self._in_rate + (output_tokens / 1_000_000) * self._out_rate

    def _roll_week(self) -> None:
        wk = _week_key(self._now())
        if wk != self._week:
            self._week = wk
            self._spent_usd = 0.0

    def spent_this_week(self) -> float:
        self._roll_week()
        return self._spent_usd

    def can_spend(self) -> bool:
        """True iff this week's spend is still under the cap. Checked before a call."""
        self._roll_week()
        return self._spent_usd < self._cap

    def record(self, input_tokens: int, output_tokens: int) -> float:
        """Add a call's cost to this week's total; returns the new weekly total."""
        self._roll_week()
        self._spent_usd += self.cost_usd(input_tokens, output_tokens)
        return self._spent_usd

    @property
    def cap_usd(self) -> float:
        return self._cap


__all__ = ["RouterBudget"]
