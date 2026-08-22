"""The spend ledger — what a turn costs and when the engine must stop.

Two ceilings that are NOT the same thing, which is the whole reason this is one
concept and not a stray field:

- `AIRE_MAX_BUDGET_USD` is handed to the SDK as `max_budget_usd`. Measured
  2026-07-20: it caps the pooled CLIENT's cumulative spend, not a turn — and a
  client that reaches it is POISONED, answering every later turn with an empty
  result and NO error (#23). So the same number is kept here to RECOGNISE the
  cut and retire the client, because the SDK will not say it.
- `AIRE_MAX_SPEND_USD` is this process's own backstop: turns refused BEFORE the
  API is called. It resets on restart, which is a known limit — a ledger that
  survives restarts is Bernard's open decision (#25).

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

    def account(self, key: str, cost: float) -> bool:
        """Bank this turn's spend; report whether the client hit its ceiling."""
        self.spend_usd += max(0.0, cost - self._seen.get(key, 0.0))
        self._seen[key] = cost
        return TURN_CAP_USD is not None and cost >= TURN_CAP_USD

    def forget(self, key: str) -> None:
        """Its spend is banked; a reborn client starts counting from zero."""
        self._seen.pop(key, None)

    @staticmethod
    def cut_event() -> dict[str, Any]:
        return {"type": "error", "error": "budget_exhausted",
                "detail": f"the turn reached the ${TURN_CAP_USD:.2f} ceiling and was "
                          "CUT — its work may be incomplete. The spent client is "
                          "retired; send the turn again to continue."}
