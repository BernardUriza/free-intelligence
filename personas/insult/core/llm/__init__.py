"""LLM client subpackage — runner-backed, no direct-Anthropic client.

The legacy direct-Anthropic Messages-API client was deleted once
the agent runner became the sole LLM backend. The conversational turn client
``AgentRunnerClient`` moved to ``khimeras_shared.runner.agent_client`` (Etapa 3
PR-1b) — it is persona-neutral transport. What remains here are the still-
persona-side building blocks:

Submodules:
- ``runner_judge_client``: ``RunnerJudgeClient`` → POST /v1/judge (one-shot
  text-only utility calls: facts, summaries, moltbook, proactive, reminders).
- ``pricing``: per-family token tracking + USD cost estimation.
- ``retry``: retry-after parsing + Full Jitter backoff timing.
- ``parsing``: WEB_SEARCH_TOOL, system-block builder, Messages API response
  parser, and a re-export of the shared ``LLMResponse`` contract (still consumed
  by the runner clients).

This __init__ is a barrel — public symbols are re-exported so existing
imports (``from personas.insult.core.llm import LLMResponse / get_usage_report``)
keep working.
"""

from personas.insult.core.llm.parsing import (
    WEB_SEARCH_TOOL,
    LLMResponse,
    _build_system_blocks,
    _parse_response_content,
)
from personas.insult.core.llm.pricing import (
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
from personas.insult.core.llm.retry import (
    _BACKOFF_CAP_5XX,
    _BACKOFF_CAP_429,
    _BACKOFF_CAP_TIMEOUT,
    _MAX_TIMEOUT_RETRIES,
    _full_jitter_backoff,
    _parse_retry_after,
)

__all__ = [
    "WEB_SEARCH_TOOL",
    "_BACKOFF_CAP_5XX",
    "_BACKOFF_CAP_429",
    "_BACKOFF_CAP_TIMEOUT",
    "_DEFAULT_FAMILY",
    "_MAX_TIMEOUT_RETRIES",
    "_PRICING",
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
