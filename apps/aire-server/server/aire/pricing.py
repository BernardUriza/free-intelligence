"""What a relayed turn cost, in dollars (backlog #32, the gateway's lent key).

The gateway lends AIRE's OWN credential to an invited key, so AIRE — not the
caller — pays Anthropic for those tokens. Anthropic reports TOKENS, never
dollars, so a per-key ceiling on that door can only bite if this module prices
them. The engine's door never needed this: the SDK hands it `total_cost_usd`
already computed.

Rates live in `prices.json` beside this file, reloaded on mtime: a price change
is Anthropic's news, not a deploy of ours.

Two biases, both deliberate, both toward NOT overspending:

- A model absent from the table is charged at the DEAREST rate in it. An
  unrecognised model must never be free — that is how a ceiling stops biting.
- List prices, even where an introductory discount is live, so the ceiling is
  reached no later than the real spend reaches it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TABLE = Path(__file__).with_name("prices.json")
# Anthropic's published cache multipliers against the model's input rate.
CACHE_WRITE = {"ephemeral_5m_input_tokens": 1.25, "ephemeral_1h_input_tokens": 2.0}
CACHE_READ = 0.1
FAST_MODE = 2.0  # `speed: "fast"` is served at twice the standard rate
_cache: tuple[float, dict[str, Any]] | None = None


def _table() -> dict[str, Any]:
    global _cache
    mtime = TABLE.stat().st_mtime
    if _cache is None or _cache[0] != mtime:
        rows = {k: v for k, v in json.loads(TABLE.read_text()).items() if isinstance(v, dict)}
        _cache = (mtime, rows)
    return _cache[1]


def rates(model: str, speed: str = "standard") -> tuple[float, float]:
    """Dollars per token, in and out. Matched by longest prefix, so a dated
    snapshot (`claude-opus-4-5-20251101`) prices as its family."""
    table = _table()
    hit = max((k for k in table if model.startswith(k)), key=len, default=None)
    row = table[hit] if hit else max(table.values(), key=lambda r: r["output"])
    factor = FAST_MODE if speed == "fast" else 1.0
    return row["input"] * factor / 1e6, row["output"] * factor / 1e6


def _cache_write_tokens(usage: dict[str, Any]) -> float:
    """Cache writes, weighted by TTL. The per-TTL breakdown is preferred; when
    only the total is present it is billed at the 1h rate — the dearer of the
    two, because guessing cheap is how a ceiling leaks."""
    breakdown = usage.get("cache_creation")
    if isinstance(breakdown, dict):
        return sum(float(breakdown.get(k, 0) or 0) * mult for k, mult in CACHE_WRITE.items())
    return float(usage.get("cache_creation_input_tokens", 0) or 0) * CACHE_WRITE["ephemeral_1h_input_tokens"]


def usd(usage: dict[str, Any] | None, model: str) -> float:
    """The dollars one relayed turn cost AIRE. Absent usage is 0.0 — a turn that
    reported nothing is priced by the caller of this function, which knows
    whether silence means 'no turn' or 'a turn we failed to read'."""
    if not isinstance(usage, dict):
        return 0.0
    per_in, per_out = rates(model or "", str(usage.get("speed") or "standard"))
    billable_in = (
        float(usage.get("input_tokens", 0) or 0)
        + _cache_write_tokens(usage)
        + float(usage.get("cache_read_input_tokens", 0) or 0) * CACHE_READ
    )
    return billable_in * per_in + float(usage.get("output_tokens", 0) or 0) * per_out
