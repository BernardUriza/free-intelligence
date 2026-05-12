"""Retry-after parsing + Full Jitter backoff for transient API failures.

Single source of truth for the retry timing policy used by `LLMClient`.
Keeping these helpers separate from the client class makes them trivial
to test in isolation (`test_llm_retry.py`) and prevents the timing math
from getting tangled in the retry loop's control flow.

Honors Anthropic's `retry-after-ms` / `retry-after` headers per
https://platform.claude.com/docs/en/api/rate-limits, avoiding the
synchronized-retry anti-pattern documented in vercel/ai#7247.

Full Jitter backoff per AWS Standard SDK and Marc Brooker's 2015 post —
beats Decorrelated Jitter on server load in his published measurements
and avoids the documented clamping bug that pins decorrelated intervals
to max_duration with only a 1/3 chance of jitter.
"""

from __future__ import annotations

import random

# Timeouts are capped separately from other retries. Each timeout is ~30s of
# dead air, so five would leave the user staring at nothing for 2+ minutes.
_MAX_TIMEOUT_RETRIES = 2

# Backoff caps per failure class — see .claude/plans/turn_resilience.md PR 0.
# 60s for 429 because Anthropic's retry-after on org-level rate limit can ask
# for that long; 30s for 5xx (overload) because they typically resolve faster;
# 10s for transport timeouts because we already cap to 2 attempts and longer
# waits compound the dead-air UX problem.
_BACKOFF_CAP_429 = 60.0
_BACKOFF_CAP_5XX = 30.0
_BACKOFF_CAP_TIMEOUT = 10.0


def _parse_retry_after(headers: object) -> float | None:
    """Read retry-after-ms (preferred, more precise) or retry-after (seconds)
    from a response's headers. Returns the wait time in seconds, or None when
    the header is absent, malformed, non-positive, or above 60s (the cap above
    which we'd rather emit our own jittered backoff than block the user).

    Anthropic documents both headers; honoring them is mandatory per
    https://platform.claude.com/docs/en/api/rate-limits and avoids the
    Vercel-AI-SDK anti-pattern of synchronized retries
    (github.com/vercel/ai/issues/7247).
    """
    if headers is None:
        return None
    get = getattr(headers, "get", None)
    if get is None:
        return None
    ms = get("retry-after-ms")
    if ms is not None:
        try:
            value = float(ms) / 1000.0
        except (TypeError, ValueError):
            value = None
        if value is not None and 0 < value <= 60:
            return value
    sec = get("retry-after")
    if sec is not None:
        try:
            value = float(sec)
        except (TypeError, ValueError):
            value = None
        if value is not None and 0 < value <= 60:
            return value
    return None


def _full_jitter_backoff(attempt: int, cap: float) -> float:
    """Full Jitter backoff per AWS Standard SDK (botocore/retries/standard.py)
    and Brooker 2015. Returns ``random.uniform(0, min(2 ** attempt, cap))``.

    Full Jitter beats Decorrelated Jitter on server load in Brooker's published
    measurements and avoids the documented clamping bug that pins decorrelated
    intervals to max_duration with only a 1/3 chance of jitter
    (thomwright.co.uk/2024/04/24/decorrelated-jitter/).
    """
    if attempt < 1:
        attempt = 1
    return random.uniform(0, min(2.0**attempt, cap))
