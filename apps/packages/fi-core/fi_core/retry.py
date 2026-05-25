"""Retry-after parsing + Full Jitter backoff for transient LLM-API failures.

Provider-agnostic resilience helpers for any LLM client (Anthropic, OpenAI,
Azure, ...). Both major providers expose a retry-after header through their SDK
response objects, but the SDK objects are not unified — so :func:`parse_retry_after`
accepts anything with a ``.get(key)`` method (dict-like headers).

Honors ``retry-after-ms`` (preferred precision, Anthropic-style) and ``retry-after``
(seconds, RFC 7231), avoiding the synchronized-retry anti-pattern documented in
vercel/ai#7247.

Full Jitter backoff per the AWS Standard SDK (botocore/retries/standard.py) and
Marc Brooker's 2015 post: it beats Decorrelated Jitter on server load in his
published measurements and avoids the clamping bug that pins decorrelated
intervals to max_duration with only a 1/3 chance of jitter
(thomwright.co.uk/2024/04/24/decorrelated-jitter/).

    from fi_core.retry import full_jitter_backoff, parse_retry_after, BACKOFF_CAP_429
    wait = parse_retry_after(err.response.headers) or full_jitter_backoff(attempt, BACKOFF_CAP_429)

Zero-dep (stdlib ``random`` only).
"""

from __future__ import annotations

import random

# Timeouts are capped separately: each timeout is ~30s of dead air, so more than
# a couple leaves the user staring at nothing for minutes.
MAX_TIMEOUT_RETRIES = 2

# Backoff caps per failure class. 60s for 429 because org-level rate-limit
# retry-after can ask for that long; 30s for 5xx (overload) which usually
# resolves faster; 10s for transport timeouts since longer waits compound the
# dead-air UX problem and timeouts are already capped to a couple of attempts.
BACKOFF_CAP_429 = 60.0
BACKOFF_CAP_5XX = 30.0
BACKOFF_CAP_TIMEOUT = 10.0

#: Upper bound on an honored retry-after: past this we'd rather emit our own
#: jittered backoff than block the caller.
MAX_HONORED_RETRY_AFTER = 60.0


def parse_retry_after(headers: object) -> float | None:
    """Extract a retry-after wait (seconds) from a response's headers.

    Accepts anything with a ``.get(key)`` method (``httpx.Headers``, plain dicts,
    test doubles). Reads ``retry-after-ms`` first (more precise), then falls back
    to ``retry-after`` (whole seconds).

    Returns ``None`` when: headers is ``None`` or has no ``.get``; the header is
    absent or unparseable; or the value is non-positive or exceeds
    :data:`MAX_HONORED_RETRY_AFTER` (we'd rather jitter our own backoff).
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
        if value is not None and 0 < value <= MAX_HONORED_RETRY_AFTER:
            return value
    sec = get("retry-after")
    if sec is not None:
        try:
            value = float(sec)
        except (TypeError, ValueError):
            value = None
        if value is not None and 0 < value <= MAX_HONORED_RETRY_AFTER:
            return value
    return None


def full_jitter_backoff(attempt: int, cap: float) -> float:
    """Full Jitter backoff: ``random.uniform(0, min(2 ** attempt, cap))``.

    ``attempt`` is 1-based (clamped up to 1). The exponential term ``2 ** attempt``
    grows the ceiling each retry; ``cap`` bounds it; the uniform draw spreads
    retries so a thundering herd doesn't re-synchronize. See module docstring for
    why Full Jitter over Decorrelated.
    """
    if attempt < 1:
        attempt = 1
    return random.uniform(0, min(2.0**attempt, cap))
