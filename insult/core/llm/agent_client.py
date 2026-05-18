"""HTTP client to the Container-Apps-resident Claude Agent SDK runner.

Insult's legacy `LLMClient` (`insult/core/llm/client.py`) talks to Anthropic
Messages API directly: it inlines the full conversation context + facts
+ disclosures as `messages[]` blocks, then receives a single-shot response.
Validated 2026-05-13 (histerical-search): 1M-context recall degrades 20-40%
on multi-hop reasoning at scale.

`AgentRunnerClient` replaces that single-shot pattern with a remote call to
the FastAPI runner in the `insult-runner` Container App. The runner hosts
the Claude Agent SDK (Python) and reads selectively from
`/data/insult-workspace/*.md` (mirrored from Postgres by a background
renderer) via Read/Grep/Glob.

## Drop-in contract

Same signature as `LLMClient.chat()` so `stages.py:448` can branch behind
the `INSULT_AGENT_SDK_USER_IDS` feature flag without changing call shape.
Returns the same `LLMResponse` dataclass.

## Auth

OAuth Max only. The runner has the credentials in
`~/.claude/.credentials.json`. The runner is reached via
`INSULT_AGENT_RUNNER_URL` with a shared bearer in
`INSULT_AGENT_RUNNER_TOKEN`. On 429 quota exhaustion the runner returns
in-character error text; the caller surfaces it normally.

## What the runner IGNORES (intentionally)

- `system_prompt`: runner reads persona.md from its own filesystem.
- `tools`: runner uses Read/Grep/Glob exclusively in Fase 2.
- `cache_breakpoints`: SDK manages its own caching.
- `tool_choice`: agent decides per turn.

## What IS preserved

- `messages[-1]['content']` becomes the agent prompt (last user text).
- `max_tokens` is forwarded only in metrics — runner uses its own cap.
- `on_timeout`: fires once after the HTTP read timeout fires the first
  time — same UX as legacy LLMClient's retry_notice.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx
import structlog

from insult.core.llm.parsing import LLMResponse

log = structlog.get_logger()


class AgentRunnerError(Exception):
    """Raised when the runner returns 5xx or invalid JSON."""


def _last_user_text(messages: list[dict]) -> str:
    """Pluck the text payload of the last user message in the API-shaped list.

    Caller (stages.py) builds Anthropic-shape messages where the final entry is
    role='user'. Its content is either a plain string OR a list of blocks (text
    + image). We only return text here; images are extracted separately by
    `_last_user_attachments`.
    """
    if not messages:
        return ""
    last = messages[-1]
    content = last.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(p for p in parts if p)
    return ""


def _last_user_attachments(messages: list[dict]) -> list[dict]:
    """Extract non-text content blocks (image, document) from the final user msg.

    Returns the raw Anthropic-shaped blocks so the runner can forward them
    directly into the SDK's streaming message format. Empty list if the
    final message has no attachments or is text-only.

    Fix v3.9.43 (REWRITE-B1): previous `_last_user_text` discarded image
    blocks silently. Symptom: Alex sent text+2 images, Insult ignored
    the images entirely. The runner now receives them as a separate
    `attachments` field and inlines them into the SDK query.
    """
    if not messages:
        return []
    last = messages[-1]
    content = last.get("content", "")
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, dict) and b.get("type") in {"image", "document"}]


class AgentRunnerClient:
    """Drop-in replacement for LLMClient that delegates to the runner.

    Constructor takes the runner URL and bearer auth. Both come from env
    (`INSULT_AGENT_RUNNER_URL` + `INSULT_AGENT_RUNNER_TOKEN`).
    """

    def __init__(
        self,
        runner_url: str,
        runner_token: str,
        *,
        timeout_s: float = 120.0,
        connect_timeout_s: float = 10.0,
    ):
        if not runner_url:
            raise ValueError("AgentRunnerClient requires runner_url")
        if not runner_token:
            raise ValueError("AgentRunnerClient requires runner_token")
        self._runner_url = runner_url.rstrip("/")
        self._runner_token = runner_token
        self._timeout_s = timeout_s
        self._connect_timeout_s = connect_timeout_s

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
        channel_id: str | None = None,
        user_id: str | None = None,
        session_uuid: str | None = None,
        fallback_model: str | None = None,
    ) -> LLMResponse:
        _ = (system_prompt, tools, max_tokens, cache_breakpoints, tool_choice, model, fallback_model)

        user_text = _last_user_text(messages)
        attachments = _last_user_attachments(messages)
        if not user_text and not attachments:
            log.warning("agent_runner_client_empty_user_text", message_count=len(messages))
            return LLMResponse(text="", model_used="agent-runner", stop_reason="empty_input")

        payload: dict[str, Any] = {
            "channel_id": channel_id or "0",
            "user_id": user_id or "0",
            # Force a placeholder when the message is image-only (rare but
            # legal — drag-and-drop with no caption). Pydantic min_length=1
            # would reject empty string on the runner side.
            "user_text": user_text or "[adjuntó solo imagen]",
        }
        if attachments:
            payload["attachments"] = attachments
            log.info(
                "agent_runner_client_attachments_forwarded",
                count=len(attachments),
                types=[a.get("type") for a in attachments],
            )
        if session_uuid:
            payload["session_uuid"] = session_uuid

        timeout = httpx.Timeout(self._timeout_s, connect=self._connect_timeout_s)
        headers = {
            "Authorization": f"Bearer {self._runner_token}",
            "Content-Type": "application/json",
        }
        url = f"{self._runner_url}/v1/turn"
        start = time.monotonic()
        timed_out_once = False

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
        except httpx.ReadTimeout as e:
            if on_timeout and not timed_out_once:
                timed_out_once = True
                try:
                    maybe = on_timeout()
                    if hasattr(maybe, "__await__"):
                        await maybe
                except Exception:
                    log.exception("agent_runner_on_timeout_callback_failed")
            log.warning(
                "agent_runner_client_timeout",
                elapsed_ms=int((time.monotonic() - start) * 1000),
                user_id=user_id,
                channel_id=channel_id,
            )
            raise AgentRunnerError(f"runner read timeout after {self._timeout_s}s") from e
        except httpx.HTTPError as e:
            log.exception(
                "agent_runner_client_http_error",
                error_type=type(e).__name__,
                elapsed_ms=int((time.monotonic() - start) * 1000),
            )
            raise AgentRunnerError(f"runner http error: {type(e).__name__}: {e}") from e

        elapsed_ms = int((time.monotonic() - start) * 1000)

        if resp.status_code >= 500:
            log.error(
                "agent_runner_client_5xx",
                status=resp.status_code,
                body_preview=resp.text[:200],
                elapsed_ms=elapsed_ms,
            )
            raise AgentRunnerError(f"runner {resp.status_code}: {resp.text[:200]}")
        if resp.status_code >= 400:
            log.error(
                "agent_runner_client_4xx",
                status=resp.status_code,
                body_preview=resp.text[:200],
                elapsed_ms=elapsed_ms,
            )
            raise AgentRunnerError(f"runner {resp.status_code}: {resp.text[:200]}")

        try:
            data = resp.json()
        except ValueError as e:
            log.exception("agent_runner_client_invalid_json", body_preview=resp.text[:200])
            raise AgentRunnerError("runner returned invalid JSON") from e

        text = data.get("text", "") or ""
        log.info(
            "agent_runner_client_turn_complete",
            text_len=len(text),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            model=data.get("model", ""),
            stop_reason=data.get("stop_reason", ""),
            tool_calls=len(data.get("tool_calls", []) or []),
            session_uuid=data.get("session_uuid"),
            elapsed_ms=elapsed_ms,
        )

        return LLMResponse(
            text=text,
            tool_calls=[],
            model_used=data.get("model", "agent-runner"),
            stop_reason=data.get("stop_reason", ""),
        )

    async def health(self) -> dict[str, Any]:
        """Probe the runner's /health endpoint."""
        timeout = httpx.Timeout(10.0, connect=5.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{self._runner_url}/health")
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            return {"status": "unreachable", "error": f"{type(e).__name__}: {e}"}
