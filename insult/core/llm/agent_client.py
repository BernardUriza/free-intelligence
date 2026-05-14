"""HTTP client to the VM-resident Claude Agent SDK runner.

SKELETON ONLY (Fase 0). This file locks the interface contract so
`stages.py` can branch behind a feature flag in Fase 2 without further
churn. All methods raise NotImplementedError until Fase 2 lands.

## Why this exists

Insult's `LLMClient` (`insult/core/llm/client.py`) talks to Anthropic
Messages API directly: it inlines the full conversation context + facts
+ disclosures as `messages[]` blocks, then receives a single-shot
response. Validated 2026-05-13 (histerical-search): 1M-context recall
degrades 20-40% on multi-hop reasoning at scale; the model treats older
context as "background" and loses anchor on what's load-bearing.

`AgentRunnerClient` replaces that single-shot pattern with a remote call
to a long-running FastAPI service on an EC2 VM. The service hosts the
Claude Agent SDK (Python), which runs an agentic loop:

  read facts/{user}.md → take action → verify → respond

The agent reads selectively from `/data/insult-workspace/*.md` (a
background renderer mirrors Postgres → markdown there) instead of
receiving the whole blob inline. Less noise → better grounding.

## Drop-in contract

Same signature as `LLMClient.chat()`:

  async def chat(
      self,
      system_prompt: str,
      messages: list[dict],
      *,
      model: str | None = None,
      tools: list[dict] | None = None,
      max_tokens: int | None = None,
      cache_breakpoints: int = 0,
      tool_choice: str | None = None,
      on_timeout: Callable | None = None,
  ) -> LLMResponse

Returns the same `LLMResponse` dataclass (text + tool_calls +
model_used + stop_reason). Caller in `stages.py:448` does NOT need to
know which backend it's talking to — it branches on
`ctx.user_id in settings.agent_sdk_user_ids` and picks one or the other.

## What the runner ignores (intentionally)

- `system_prompt`: the runner reads `persona.md` from the workspace
  itself (mtime-aware). Caller's blob is dropped.
- `tools`: runner uses Read/Grep/Glob exclusively in Fase 2; Write
  added to a sandbox in Fase 3. Caller's tool list is dropped.
- `cache_breakpoints`: Agent SDK manages its own caching strategy.
- `tool_choice`: agent decides; runner has no mode switch.

What IS preserved:

- The last user message in `messages[-1]` is the prompt sent to the
  agent. Everything before is in the workspace already.
- `max_tokens` is passed through as the agent's response cap.
- `on_timeout` callback fires when the agent exceeds the per-turn
  budget (default 90s, configurable).

## Auth

OAuth Max only (Bernard's plan). The runner has
`~/.claude/.credentials.json` from the EC2 bootstrap. No API key
fallback — on 429 quota exhaustion the runner returns an in-character
error and the caller surfaces it via `core/errors.py`.

## Status

Fase 0: skeleton committed. Methods raise NotImplementedError.
Fase 2: implementation lands + feature flag in stages.py.
Fase 3: Bernard's ID → all IDs in feature flag.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog

from insult.core.llm.parsing import LLMResponse

log = structlog.get_logger()


class AgentRunnerClient:
    """Drop-in replacement for LLMClient that delegates to the VM runner.

    Constructor takes the runner URL and the bearer auth shared with the
    runner. Both come from env (`INSULT_AGENT_RUNNER_URL` +
    `INSULT_AGENT_RUNNER_TOKEN`) — set in Fase 2 deploy.
    """

    def __init__(
        self,
        runner_url: str,
        runner_token: str,
        *,
        timeout_s: float = 90.0,
    ):
        if not runner_url:
            raise ValueError("AgentRunnerClient requires runner_url")
        if not runner_token:
            raise ValueError("AgentRunnerClient requires runner_token")
        self._runner_url = runner_url.rstrip("/")
        self._runner_token = runner_token
        self._timeout_s = timeout_s

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict],
        *,
        model: str | None = None,
        tools: list[dict] | None = None,
        max_tokens: int | None = None,
        cache_breakpoints: int = 0,
        tool_choice: str | None = None,
        on_timeout: Callable[[], Any] | None = None,
    ) -> LLMResponse:
        """Send a turn to the Agent SDK runner. Returns when the agent
        finishes its loop (text response ready) or raises on error.

        Only the last user message in `messages` is forwarded — earlier
        turns are read from the workspace by the agent itself. The other
        arguments preserve the LLMClient.chat() shape so callers can
        swap implementations behind a feature flag without code change:

        - `system_prompt`: ignored; runner reads `persona.md` from workspace.
        - `model`: ignored; runner picks model from its own config.
        - `tools`: ignored; runner uses Read/Grep/Glob (Fase 2 — see plan).
        - `cache_breakpoints`: ignored; SDK manages its own caching.
        - `tool_choice`: ignored; agent decides per turn.
        - `max_tokens`: passed through as the agent's response cap.
        - `on_timeout`: fires when agent exceeds 90s per-turn budget.
        """
        _ = (system_prompt, messages, model, tools, max_tokens, cache_breakpoints, tool_choice, on_timeout)
        raise NotImplementedError(
            "AgentRunnerClient.chat() not implemented yet. "
            "Lands in Fase 2 of the Agent SDK migration. "
            "See .claude/plans/insult_agent_sdk_migration.md"
        )

    async def health(self) -> dict[str, Any]:
        """Probe the runner's /health endpoint. Returns {status, ready,
        session_count, last_turn_age_s}. Used by Insult Container App's
        own /debug/health to surface runner state.
        """
        raise NotImplementedError(
            "AgentRunnerClient.health() not implemented yet. Fase 2."
        )
