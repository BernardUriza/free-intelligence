"""Per-family token usage tracking + cost estimation.

Resets on redeploy (in-memory counters). Pricing tables are per-family
(haiku/sonnet/opus) so a 3-tier router producing per-call costs is
attributed correctly. Unknown models fall back to Sonnet rates —
conservative for Haiku (slight overestimate) and safe for Opus (never
hides a blown budget).

Verified against https://platform.claude.com/docs/en/about-claude/pricing
on 2026-05-05. Opus pricing dropped 3x from 4.1 → 4.5+ (4.5/4.6/4.7
share the new rate). Sonnet and Haiku rates have been stable across 4.x.
"""

from __future__ import annotations

# Pricing per million tokens, per model family.
_PRICING: dict[str, dict[str, float]] = {
    "haiku": {"input": 1.00, "output": 5.00, "cache_read": 0.10, "cache_create": 1.25},
    "sonnet": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_create": 3.75},
    "opus": {"input": 5.00, "output": 25.00, "cache_read": 0.50, "cache_create": 6.25},
}
_DEFAULT_FAMILY = "sonnet"


def _resolve_family(model: str) -> str:
    """Map a full model id to its pricing family.

    claude-haiku-4-5-20251001 → 'haiku', claude-sonnet-4-6 → 'sonnet', etc.
    Unknown models default to Sonnet (conservative — overestimates Haiku
    slightly but never understates Opus, which would hide a blown budget).
    """
    lower = model.lower()
    for family in _PRICING:
        if family in lower:
            return family
    return _DEFAULT_FAMILY


def _zero_bucket() -> dict[str, int]:
    return {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_create_tokens": 0, "requests": 0}


# Per-family token counters. Keys populated lazily as families are seen.
_usage_by_family: dict[str, dict[str, int]] = {}
_errors_total = 0


def record_usage(
    input_tokens: int,
    output_tokens: int,
    cache_read: int = 0,
    cache_create: int = 0,
    model: str = "",
) -> None:
    """Accumulate token usage for cost tracking, keyed by model family."""
    family = _resolve_family(model) if model else _DEFAULT_FAMILY
    bucket = _usage_by_family.setdefault(family, _zero_bucket())
    bucket["input_tokens"] += input_tokens
    bucket["output_tokens"] += output_tokens
    bucket["cache_read_tokens"] += cache_read
    bucket["cache_create_tokens"] += cache_create
    bucket["requests"] += 1


def _record_error() -> None:
    global _errors_total
    _errors_total += 1


def get_usage_report() -> dict:
    """Return accumulated usage with estimated cost in USD, broken out per family."""
    per_family: dict[str, dict] = {}
    total_tokens_in = 0
    total_tokens_out = 0
    total_cache_read = 0
    total_cache_create = 0
    total_requests = 0
    total_cost = 0.0

    for family, bucket in _usage_by_family.items():
        pricing = _PRICING.get(family, _PRICING[_DEFAULT_FAMILY])
        cost_input = (bucket["input_tokens"] / 1_000_000) * pricing["input"]
        cost_output = (bucket["output_tokens"] / 1_000_000) * pricing["output"]
        cost_cache_read = (bucket["cache_read_tokens"] / 1_000_000) * pricing["cache_read"]
        cost_cache_create = (bucket["cache_create_tokens"] / 1_000_000) * pricing["cache_create"]
        family_cost = cost_input + cost_output + cost_cache_read + cost_cache_create

        per_family[family] = {
            "tokens": dict(bucket),
            "cost_usd": round(family_cost, 4),
        }

        total_tokens_in += bucket["input_tokens"]
        total_tokens_out += bucket["output_tokens"]
        total_cache_read += bucket["cache_read_tokens"]
        total_cache_create += bucket["cache_create_tokens"]
        total_requests += bucket["requests"]
        total_cost += family_cost

    return {
        "tokens": {
            "input": total_tokens_in,
            "output": total_tokens_out,
            "cache_read": total_cache_read,
            "cache_create": total_cache_create,
            "total": total_tokens_in + total_tokens_out,
        },
        "requests": total_requests,
        "errors": _errors_total,
        "cost_usd": {"total": round(total_cost, 4)},
        "per_family": per_family,
        "avg_tokens_per_request": round((total_tokens_in + total_tokens_out) / max(total_requests, 1)),
        "note": "Resets on redeploy. Pricing is per-family (haiku/sonnet/opus); unknown models default to sonnet rates.",
    }
