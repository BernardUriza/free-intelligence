"""What a drained `result` event says about money and tokens — read by the
door (`messages.py`), the turn ledger (`turn.py`) and the detached drainer."""

from typing import Any


def _usage(event: dict[str, Any]) -> dict[str, Any] | None:
    """A `result` comes in TWO shapes — SDK dataclass and flattened dict; reading
    only the first billed an invited key (#32d) nothing (silent $0). Both here."""
    result = event.get("result")
    usage = getattr(result, "usage", None) or (result.get("usage") if isinstance(result, dict) else None)
    return usage if isinstance(usage, dict) else None


def turn_cost(event: dict[str, Any]) -> float:
    """The dollars a `result` reports (0.0 when absent), off the drained stream."""
    usage = _usage(event)
    cost = usage.get("total_cost_usd") if usage else None
    return float(cost) if cost else 0.0


def turn_tokens(event: dict[str, Any]) -> dict[str, int]:
    """The cache breakdown for aire_spend: cache_read ≫ cache_creation is warm,
    the inverse a cold re-cache; empty (→ null) when the turn reports no usage."""
    usage = _usage(event)
    if not usage:
        return {}
    return {"cache_read": int(usage.get("cache_read_input_tokens") or 0),
            "cache_creation": int(usage.get("cache_creation_input_tokens") or 0),
            "input_tokens": int(usage.get("input_tokens") or 0)}
