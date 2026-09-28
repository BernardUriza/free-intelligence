"""HTTP client to the persona-runner's POST /v1/judge endpoint.

Lets a utility caller (fact extraction, the consolidation job, any future
one-shot LLM need) delegate execution to the runner instead of holding its own
Anthropic API key. The runner already has OAuth Max wired; this collapses the
auth surface to one place.

Sibling of `agent_client.py` and deliberately a SUBSET of it: `AgentRunnerClient`
targets `/v1/turn` (a persona's conversational turn, with session state);
`RunnerJudgeClient` targets `/v1/judge` (a one-shot, stateless text call with a
caller-supplied system prompt). Same env pair on the wire: `PERSONA_RUNNER_URL` +
`PERSONA_RUNNER_TOKEN`.

Shape B per [[mcp-shape-b-canonical]]: the caller builds the prompt, this client
EXECUTES it against the runner, the caller parses the result. Three layers, three
responsibilities, zero LLM credentials in the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
import structlog

log = structlog.get_logger()

__all__ = ["JudgeResponse", "RunnerJudgeClient", "flatten_utility_messages"]


def flatten_utility_messages(messages: list[dict[str, Any]]) -> tuple[str, list[dict]]:
    """Anthropic-shape `messages` → the judge's one-shot `(user_text, attachments)`.

    Only `user` turns count; list content splits into concatenated text plus
    image/document blocks. Shared by this HTTP client and the runner's
    in-process judge, so both read a prompt the same way.
    """
    user_text = ""
    attachments: list[dict] = []
    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = msg.get("content", "")
        if isinstance(content, str):
            user_text += ("\n\n" if user_text else "") + content
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and block.get("text"):
                    user_text += ("\n\n" if user_text else "") + block["text"]
                elif block.get("type") in {"image", "document"}:
                    attachments.append(block)
    return user_text, attachments


@dataclass
class JudgeResponse:
    """The shape a utility caller consumes — only the fields anyone reads."""

    text: str
    model_used: str = ""
    stop_reason: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


class RunnerJudgeClient:
    """HTTP client to /v1/judge. Exposes `utility_call` for one-shot text calls.

    NOT thread-safe; one client per host process is sufficient. The httpx
    AsyncClient is created lazily on first call and reused for this instance's
    lifetime.
    """

    def __init__(
        self,
        runner_url: str,
        token: str,
        *,
        timeout_s: float = 240.0,
    ) -> None:
        # Default 240s (4 min). A judge call over a large fact set measured 61s
        # in prod (2026-05-19); a too-tight default produced ClosedResourceError
        # when the runner answered *after* the client gave up.
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
    ) -> JudgeResponse:
        """One-shot utility call against the runner's /v1/judge.

        Args:
            system_prompt: passed verbatim to the runner. NOT a persona file —
                the caller decides what the LLM sees.
            messages: Anthropic shape (`[{"role": "user", "content": "..."}]`).
                Only single-turn use is supported — /v1/judge is one-shot. List
                content splits into text (concatenated) + image/document blocks
                forwarded as `attachments`.
            model: model id to request. Falsy → the runner's own judge-model
                default (Haiku class).
            max_tokens: max generation tokens.

        Returns:
            JudgeResponse with text + token counts + stop_reason.

        Raises:
            httpx.HTTPError on a transport failure or a non-2xx from the runner —
            callers treat fact extraction as best-effort and swallow it.
        """
        user_text, attachments = flatten_utility_messages(messages)
        if not user_text.strip():
            raise ValueError("RunnerJudgeClient.utility_call: messages produced empty user_text")

        payload: dict[str, Any] = {
            "system_prompt": system_prompt,
            "user_text": user_text,
            "max_tokens": max_tokens,
        }
        if attachments:
            payload["attachments"] = attachments
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
        log.info(
            "runner_judge_complete",
            model=data.get("model", ""),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            stop_reason=data.get("stop_reason", ""),
        )
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
