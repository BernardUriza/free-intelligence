"""Retry-after parsing + Full Jitter backoff — re-exports from `shared.llm`.

The implementation moved to `shared/llm/retry.py` so ALICE (OpenAI) and
Insult (Anthropic) can share the same timing math. Existing Insult callers
that import `_parse_retry_after` or `_full_jitter_backoff` from here keep
working through the aliases below.

New code: import from `shared.llm` directly.
"""

from __future__ import annotations

from shared.llm.retry import (
    BACKOFF_CAP_5XX as _BACKOFF_CAP_5XX,
)
from shared.llm.retry import (
    BACKOFF_CAP_429 as _BACKOFF_CAP_429,
)
from shared.llm.retry import (
    BACKOFF_CAP_TIMEOUT as _BACKOFF_CAP_TIMEOUT,
)
from shared.llm.retry import (
    MAX_TIMEOUT_RETRIES as _MAX_TIMEOUT_RETRIES,
)
from shared.llm.retry import (
    full_jitter_backoff as _full_jitter_backoff,
)
from shared.llm.retry import (
    parse_retry_after as _parse_retry_after,
)

__all__ = [
    "_BACKOFF_CAP_5XX",
    "_BACKOFF_CAP_429",
    "_BACKOFF_CAP_TIMEOUT",
    "_MAX_TIMEOUT_RETRIES",
    "_full_jitter_backoff",
    "_parse_retry_after",
]
