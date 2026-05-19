"""HTTP client to the agent runner's POST /v1/judge endpoint.

Lets the fact-consolidation job (and any future utility caller) delegate
one-shot LLM execution to the runner instead of holding its own Anthropic
API key. The runner already has OAuth Max wired; this client lets us
collapse the auth surface to one place.

Shape B per [[mcp-shape-b-canonical]]: fi-core builds the prompt (via
its MCP tools), this client EXECUTES the prompt against the runner,
fi-core parses the result. Three layers, three responsibilities, zero
LLM credentials in the consolidator.

This is intentionally a SUBSET of the legacy LLMClient surface — only
`utility_call` is implemented because that's all the consolidator needs.
If a future caller wants more (chat-style turns), use AgentRunnerClient
(`agent_client.py`) which targets /v1/turn.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
import structlog

log = structlog.get_logger()


@dataclass
class JudgeResponse:
    """Mirrors the shape that LLMClient.utility_call returned, so callers
    that previously consumed `LLMResponse` (e.g. memory_consolidator's
    `_call_judge`) work without code change. Only the fields the
    consolidator actually reads are exposed."""

    text: str
    model_used: str = ""
    stop_reason: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


class RunnerJudgeClient:
    """HTTP client to /v1/judge. Quacks like LLMClient for utility_call.

    Usage (drop-in for memory_consolidator):
        client = RunnerJudgeClient(runner_url=..., token=...)
        resp = await client.utility_call(
            system_prompt="You are a curator...",
            messages=[{"role": "user", "content": "..."}],
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
        )
        # resp.text is the raw judge output; consolidator parses it
        # (or, in Shape B, hands it to fi-core's parse_consolidation_result)

    NOT thread-safe; one client per consolidator run is sufficient. The
    httpx AsyncClient is created lazily on first call and reused for the
    lifetime of this instance.
    """

    def __init__(
        self,
        runner_url: str,
        token: str,
        *,
        timeout_s: float = 60.0,
    ) -> None:
        if not runner_url:
            raise ValueError("RunnerJudgeClient: runner_url is required")
        if not token:
            raise ValueError("RunnerJudgeClient: token is required")
        self._runner_url = runner_url.rstrip("/")
        self._token = token
        self._timeout = timeout_s
        self._http: httpx.AsyncClient | None = None

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self._timeout)
        return self._http

    async def utility_call(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        tools: list | None = None,
        tool_choice: dict | None = None,
    ) -> JudgeResponse:
        """Drop-in replacement for LLMClient.utility_call.

        Args:
            system_prompt: passed verbatim to the runner. NOT persona.md
                — the caller decides what the LLM sees.
            messages: standard Anthropic shape (`[{"role": "user",
                "content": "..."}]`). Only single-turn use is supported
                — the runner's /v1/judge endpoint is one-shot.
            model: model id to request. Defaults to runner's
                AGENT_RUNNER_JUDGE_MODEL env (Haiku class).
            max_tokens: max generation tokens. Default 4096.
            tools / tool_choice: IGNORED — /v1/judge is text-only. The
                params are kept in the signature to mirror utility_call's
                shape so memory_consolidator does not need to know which
                client implementation it has.

        Returns:
            JudgeResponse with text + token counts + stop_reason.
        """
        if tools is not None or tool_choice is not None:
            log.warning(
                "runner_judge_tool_args_ignored",
                note="/v1/judge is text-only; tools/tool_choice not forwarded",
            )
        # Collapse the messages list to a single user_text string —
        # /v1/judge is one-shot, no conversation continuity. The
        # consolidator always sends [{"role": "user", "content": "..."}]
        # so this is a clean fit.
        user_text = ""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user" and isinstance(content, str):
                user_text += ("\n\n" if user_text else "") + content
            # Ignore non-user messages — utility_call shouldn't have them
            # but defensive in case a caller passes assistant/system roles.

        if not user_text.strip():
            raise ValueError("RunnerJudgeClient.utility_call: messages produced empty user_text")

        payload: dict[str, Any] = {
            "system_prompt": system_prompt,
            "user_text": user_text,
            "max_tokens": max_tokens,
        }
        if model:
            payload["model"] = model

        http = await self._client()
        resp = await http.post(
            f"{self._runner_url}/v1/judge",
            json=payload,
            headers={"Authorization": f"Bearer {self._token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        return JudgeResponse(
            text=data.get("text", ""),
            model_used=data.get("model", ""),
            stop_reason=data.get("stop_reason", ""),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
        )

    async def aclose(self) -> None:
        """Close the underlying httpx client. Idempotent."""
        if self._http is not None:
            await self._http.aclose()
            self._http = None
