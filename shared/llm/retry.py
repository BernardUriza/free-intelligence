"""Retry-after parsing + Full Jitter backoff for transient API failures.

Shared by Insult (Anthropic) and ALICE (OpenAI). Both providers expose the
retry-after header through their SDK response objects, but the SDK objects
themselves are not unified. This module accepts anything with a `.get(key)`
method — dict-like headers — keeping it provider-agnostic.

Honors `retry-after-ms` (preferred, more precise; Anthropic-style) and
`retry-after` (seconds; standard RFC 7231) per
https://platform.claude.com/docs/en/api/rate-limits, avoiding the
synchronized-retry anti-pattern documented in vercel/ai#7247.

Full Jitter backoff per AWS Standard SDK and Marc Brooker's 2015 post —
beats Decorrelated Jitter on server load in his published measurements
and avoids the documented clamping bug that pins decorrelated intervals
to max_duration with only a 1/3 chance of jitter.

Insult's original module lives at `insult/core/llm/retry.py`; that file
became a thin re-export shim once this shared module landed. ALICE's
copy in `alice/core/llm.py` also got purged in favor of these helpers.
"""

from __future__ import annotations

import random

# Timeouts are capped separately from other retries. Each timeout is ~30s of
# dead air, so five would leave the user staring at nothing for 2+ minutes.
MAX_TIMEOUT_RETRIES = 2

# Backoff caps per failure class — originally tuned for Insult in
# .claude/plans/turn_resilience.md PR 0. 60s for 429 because Anthropic's
# retry-after on org-level rate limit can ask for that long; 30s for 5xx
# (overload) because they typically resolve faster; 10s for transport
# timeouts because we already cap to 2 attempts and longer waits compound
# the dead-air UX problem.
BACKOFF_CAP_429 = 60.0
BACKOFF_CAP_5XX = 30.0
BACKOFF_CAP_TIMEOUT = 10.0


def parse_retry_after(headers: object) -> float | None:
    """Extract retry-after wait time in seconds from a response's headers.

    Accepts anything with a `.get(key)` method (real `httpx.Headers`, plain
    dicts, MagicMock). Reads `retry-after-ms` first (preferred precision),
    then falls back to `retry-after` (whole seconds).

    Returns None when:
      - headers is None or has no `.get` method
      - header is absent or unparseable
      - parsed value is non-positive or > 60 seconds (we'd rather emit
        our own jittered backoff than block the user that long)
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


def full_jitter_backoff(attempt: int, cap: float) -> float:
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
