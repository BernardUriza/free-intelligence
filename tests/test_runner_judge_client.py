"""Tests for `insult.core.llm.runner_judge_client.RunnerJudgeClient`.

The client is a thin httpx wrapper around the runner's POST /v1/judge
endpoint, BUT it has shape contracts (mirror LLMClient.utility_call) +
defensive collapse logic (single-turn user_text, ignore tools args)
that bit us once in prod (v3.9.87 timeout bug). These tests pin the
contract + the defensive paths.

httpx's MockTransport is used instead of respx (extra dep) — Python
3.14 conda env doesn't ship respx and we want to stay lean.
"""

from __future__ import annotations

import json

import httpx
import pytest

from personas.insult.core.llm.runner_judge_client import (
    JudgeResponse,
    RunnerJudgeClient,
)


def _make_transport(handler):
    """Wrap a request->response handler into a MockTransport injectable
    into the client's internal httpx instance."""
    return httpx.MockTransport(handler)


def test_constructor_requires_url_and_token():
    """Missing url OR token raises at construction — fail-fast,
    avoid silent 401s in prod."""
    with pytest.raises(ValueError, match="runner_url is required"):
        RunnerJudgeClient(runner_url="", token="t")
    with pytest.raises(ValueError, match="token is required"):
        RunnerJudgeClient(runner_url="https://x", token="")


def test_constructor_strips_trailing_slash():
    """Tolerate caller-supplied trailing slashes — both
    `https://x/` and `https://x` produce the same POST URL."""
    c = RunnerJudgeClient(runner_url="https://x/", token="t")
    assert c._runner_url == "https://x"
    c2 = RunnerJudgeClient(runner_url="https://x", token="t")
    assert c2._runner_url == "https://x"


def test_constructor_default_timeout_240s():
    """Pinned: 240s default per v3.9.87. The 60s default that shipped
    in v3.9.82 caused production data loss when the runner responded
    at 61s. If this drops below ~120s, the consolidator regresses."""
    c = RunnerJudgeClient(runner_url="https://x", token="t")
    assert c._timeout == 240.0


@pytest.mark.asyncio
async def test_utility_call_collapses_user_messages():
    """Multiple user messages → single user_text concatenated with \\n\\n.
    Non-user roles dropped (defensive). This matches the consolidator's
    actual usage shape (always a single user msg) without breaking on
    accidental multi-msg input."""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={
                "text": "ok",
                "model": "haiku",
                "stop_reason": "end_turn",
                "input_tokens": 1,
                "output_tokens": 2,
            },
        )

    c = RunnerJudgeClient(runner_url="https://x", token="t")
    c._http = httpx.AsyncClient(transport=_make_transport(handler))

    resp = await c.utility_call(
        "You are X",
        [
            {"role": "user", "content": "first"},
            {"role": "user", "content": "second"},
            {"role": "system", "content": "should be dropped"},
            {"role": "assistant", "content": "also dropped"},
        ],
        model="haiku",
        max_tokens=100,
    )

    # Request shape
    assert captured["url"] == "https://x/v1/judge"
    assert captured["auth"] == "Bearer t"
    assert captured["body"]["system_prompt"] == "You are X"
    assert captured["body"]["user_text"] == "first\n\nsecond"
    assert captured["body"]["model"] == "haiku"
    assert captured["body"]["max_tokens"] == 100

    # Response shape preserved
    assert isinstance(resp, JudgeResponse)
    assert resp.text == "ok"
    assert resp.model_used == "haiku"
    assert resp.stop_reason == "end_turn"
    assert resp.input_tokens == 1
    assert resp.output_tokens == 2

    await c.aclose()


@pytest.mark.asyncio
async def test_utility_call_raises_on_empty_user_text():
    """If `messages` produces no user_text (all non-user roles, or
    empty content), raise ValueError instead of POSTing an empty body
    that the runner would reject with a less-useful 422."""
    c = RunnerJudgeClient(runner_url="https://x", token="t")
    with pytest.raises(ValueError, match="empty user_text"):
        await c.utility_call("sys", [{"role": "assistant", "content": "x"}])
    await c.aclose()


@pytest.mark.asyncio
async def test_utility_call_omits_model_when_none():
    """When model=None, the request body MUST NOT include a `model`
    key — that lets the runner fall back to AGENT_RUNNER_JUDGE_MODEL.
    Sending model=null would be ambiguous to the FastAPI Pydantic layer."""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"text": "ok"})

    c = RunnerJudgeClient(runner_url="https://x", token="t")
    c._http = httpx.AsyncClient(transport=_make_transport(handler))

    await c.utility_call("sys", [{"role": "user", "content": "hi"}])
    assert "model" not in captured["body"]
    await c.aclose()


@pytest.mark.asyncio
async def test_utility_call_ignores_tools_args_with_warning(caplog):
    """The legacy LLMClient.utility_call accepts `tools` + `tool_choice`.
    /v1/judge is text-only — those args MUST be silently ignored (not
    forwarded, not raised) so consolidator code that previously
    consumed LLMClient doesn't need to know which client it has."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        # `tools` / `tool_choice` MUST NOT be in the forwarded body
        assert "tools" not in body
        assert "tool_choice" not in body
        return httpx.Response(200, json={"text": "ok"})

    c = RunnerJudgeClient(runner_url="https://x", token="t")
    c._http = httpx.AsyncClient(transport=_make_transport(handler))

    await c.utility_call(
        "sys",
        [{"role": "user", "content": "hi"}],
        tools=[{"name": "ignored"}],
        tool_choice={"type": "any"},
    )
    await c.aclose()


@pytest.mark.asyncio
async def test_utility_call_raises_on_http_4xx():
    """Runner returns 401/422/500 — propagate via httpx.HTTPStatusError
    so the consolidator surfaces a real error (not silently empty)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "bad token"})

    c = RunnerJudgeClient(runner_url="https://x", token="t")
    c._http = httpx.AsyncClient(transport=_make_transport(handler))

    with pytest.raises(httpx.HTTPStatusError):
        await c.utility_call("sys", [{"role": "user", "content": "hi"}])
    await c.aclose()


@pytest.mark.asyncio
async def test_aclose_is_idempotent():
    """aclose() called twice does not raise — defensive cleanup
    for `finally` blocks in the consolidator."""
    c = RunnerJudgeClient(runner_url="https://x", token="t")
    # Force lazy client init
    c._http = httpx.AsyncClient()
    await c.aclose()
    assert c._http is None
    # Second call is a no-op
    await c.aclose()
    assert c._http is None


@pytest.mark.asyncio
async def test_response_missing_fields_defaults_to_zeros():
    """If the runner returns a partial response (e.g. {"text": "..."}
    only), defaults to 0/"" for missing fields — matches LLMResponse
    shape so downstream code doesn't break on KeyError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"text": "minimal"})

    c = RunnerJudgeClient(runner_url="https://x", token="t")
    c._http = httpx.AsyncClient(transport=_make_transport(handler))

    resp = await c.utility_call("sys", [{"role": "user", "content": "hi"}])
    assert resp.text == "minimal"
    assert resp.model_used == ""
    assert resp.stop_reason == ""
    assert resp.input_tokens == 0
    assert resp.output_tokens == 0
    await c.aclose()
