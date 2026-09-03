"""The spend ledger — what a turn costs and when the engine must stop.

Two ceilings that are NOT the same thing, which is the whole reason this is one
concept and not a stray field:

- `AIRE_MAX_BUDGET_USD` is handed to the SDK as `max_budget_usd`. Measured
  2026-07-20: it caps the pooled CLIENT's cumulative spend, not a turn — and a
  client that reaches it is POISONED, answering every later turn with an empty
  result and NO error (#23). So the same number is kept here to RECOGNISE the
  cut and retire the client, because the SDK will not say it. Since 2026-09-03
  only a METERED client carries the cap (`options.build_options`): an OAuth
  client's dollars are nominal, and cutting it every ~3 crisis turns only bought
  a fresh cache-creation per rebirth — so the recognition is metered-only too.
- `AIRE_MAX_SPEND_USD` is this process's own backstop: turns refused BEFORE the
  API is called. It resets on restart, which is a known limit — a ledger that
  survives restarts is Bernard's open decision (#25). Since 2026-08-26 it counts
  METERED dollars only (`credentials.is_metered`): an OAuth turn's cost is
  nominal — the Max subscription already paid — and banking it against the
  ceiling turned a card backstop into a scheduled outage (every ~$20 of nominal
  spend, every persona went mute until a restart).

`account` adds the DELTA, never the total: `total_cost_usd` is the client's
CUMULATIVE spend, so banking it whole would N-count the same dollars over N
turns.
"""

from __future__ import annotations

import os
from typing import Any

MAX_SPEND_USD = float(os.environ["AIRE_MAX_SPEND_USD"]) if os.environ.get("AIRE_MAX_SPEND_USD") else None
TURN_CAP_USD = float(os.environ["AIRE_MAX_BUDGET_USD"]) if os.environ.get("AIRE_MAX_BUDGET_USD") else None


class Ledger:
    def __init__(self) -> None:
        self.spend_usd = 0.0  # cumulative, process lifetime — the global backstop
        self._seen: dict[str, float] = {}  # per-client last accumulated cost, for the delta

    def exhausted(self) -> bool:
        return MAX_SPEND_USD is not None and self.spend_usd >= MAX_SPEND_USD

    def refusal(self) -> str:
        return f"cumulative spend ${self.spend_usd:.2f} >= ceiling ${MAX_SPEND_USD:.2f}"

    def account(self, key: str, cost: float, metered: bool = True) -> tuple[float, bool]:
        """Bank this turn's spend; return (its delta, whether the client hit its
        ceiling). Only metered spend moves the process ceiling, and only a
        metered client HAS a ceiling to hit; the delta is returned either way so
        the caller can still record nominal spend in `aire_spend` — the monthly
        ledger keeps the whole story."""
        delta = max(0.0, cost - self._seen.get(key, 0.0))
        if metered:
            self.spend_usd += delta
        self._seen[key] = cost
        return delta, metered and TURN_CAP_USD is not None and cost >= TURN_CAP_USD

    def forget(self, key: str) -> None:
        """Its spend is banked; a reborn client starts counting from zero."""
        self._seen.pop(key, None)

    def adopt(self, key: str) -> None:
        """A NEW client was just built for this key — take its predecessor's
        total off the books, because that number belongs to a process that no
        longer exists and the newborn counts from zero.

        Left in place it does not merely go stale, it INVERTS the meter:
        `account`'s `max(0.0, cost - seen)` clamps every turn to $0 until the
        newborn out-spends the dead one, so real turns burning real money move
        neither the ceiling nor `aire_spend`. Until 2026-08-23 only `_retire`
        (#23) forgot, and a pool of two slots evicts constantly — eviction, the
        COMMON exit, forgot nothing. Measured: a client banking 0.028/0.030/0.033
        followed by a reborn one at 0.025 banked **$0.00** for a paid turn.

        It lives here rather than at the eviction site because this is where the
        `_seen` invariant is stated, and BIRTH is the only moment it becomes
        true again — whatever route the previous client took out of the pool."""
        self._seen.pop(key, None)

    @staticmethod
    def cut_event() -> dict[str, Any]:
        return {"type": "error", "error": "budget_exhausted",
                "detail": f"the turn reached the ${TURN_CAP_USD:.2f} ceiling and was "
                          "CUT — its work may be incomplete. The spent client is "
                          "retired; send the turn again to continue."}
