"""Claude API client subpackage.

Submodules:
- ``pricing``: per-family token tracking + USD cost estimation.
- ``retry``: retry-after parsing + Full Jitter backoff timing.
- ``parsing``: LLMResponse, WEB_SEARCH_TOOL, system-block builder,
  Messages API response parser.
- ``client``: LLMClient with _send retry loop, _recover_from_break,
  chat (user-facing guards), utility_call (no guards).

This __init__ is a barrel — every public symbol is re-exported so
that ``from insult.core.llm import LLMClient`` (and the private
helpers used by tests) keeps working after the F4 refactor.
"""

from insult.core.llm.client import (
    _ANTI_PATTERN_FALLBACK_THRESHOLD,
    LLMClient,
)
from insult.core.llm.parsing import (
    WEB_SEARCH_TOOL,
    LLMResponse,
    _build_system_blocks,
    _parse_response_content,
)
from insult.core.llm.pricing import (
    _DEFAULT_FAMILY,
    _PRICING,
    _errors_total,
    _record_error,
    _resolve_family,
    _usage_by_family,
    _zero_bucket,
    get_usage_report,
    record_usage,
)
from insult.core.llm.retry import (
    _BACKOFF_CAP_5XX,
    _BACKOFF_CAP_429,
    _BACKOFF_CAP_TIMEOUT,
    _MAX_TIMEOUT_RETRIES,
    _full_jitter_backoff,
    _parse_retry_after,
)

__all__ = [
    "WEB_SEARCH_TOOL",
    "_ANTI_PATTERN_FALLBACK_THRESHOLD",
    "_BACKOFF_CAP_5XX",
    "_BACKOFF_CAP_429",
    "_BACKOFF_CAP_TIMEOUT",
    "_DEFAULT_FAMILY",
    "_MAX_TIMEOUT_RETRIES",
    "_PRICING",
    "LLMClient",
    "LLMResponse",
    "_build_system_blocks",
    "_errors_total",
    "_full_jitter_backoff",
    "_parse_response_content",
    "_parse_retry_after",
    "_record_error",
    "_resolve_family",
    "_usage_by_family",
    "_zero_bucket",
    "get_usage_report",
    "record_usage",
]
