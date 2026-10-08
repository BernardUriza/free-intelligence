"""PR-4b — HostRouterLLM unit test (no network).

Verifies the demux host's reception brain maps an instruction + input onto
fi_runner and reads back a token-accounted result, with NO persona/guard
machinery (the host is a router, not a character). fi_runner is mocked so CI
never touches AIRE's door.

2026-08-29: the transport moved from `CodexBackend` (Azure/gpt-4.1) to
`AIREBackend` in the fi-runner backend consolidation, so the fixture patches
the new symbol and the env the backend reads.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

import demux_ai.host_llm as host_llm


class _FakeResult:
    def __init__(self) -> None:
        self.text = "ROUTE: insult"
        self.usage = {"input_tokens": 12, "output_tokens": 3}
        self.session_id = "host-test"
        # AIRE reports the model that ANSWERED, off the AssistantMessages.
        self.model = "claude-haiku-4-5-20251001"


class _FakeRunner:
    last_kwargs: ClassVar[dict] = {}

    def __init__(self, **kwargs) -> None:
        _FakeRunner.last_kwargs = kwargs

    async def run(self, _prompt: str) -> _FakeResult:
        return _FakeResult()


class _FakeBackend:
    last_kwargs: ClassVar[dict] = {}

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        _FakeBackend.last_kwargs = kwargs


@pytest.fixture
def patched(monkeypatch):
    monkeypatch.setattr(host_llm, "AIREBackend", _FakeBackend)
    monkeypatch.setattr(host_llm, "Runner", _FakeRunner)
    monkeypatch.setenv("AIRE_GATE_URL", "https://gate.example.test")
    monkeypatch.setenv("AIRE_AUTH_TOKEN", "test-token")
    monkeypatch.delenv("HOST_ROUTER_PROJECT", raising=False)
    monkeypatch.delenv("HOST_ROUTER_MODEL", raising=False)


@pytest.mark.asyncio
async def test_complete_returns_token_accounted_result(patched):
    client = host_llm.HostRouterLLM()
    result = await client.complete("Classify the target persona.", "hola")
    assert result.text == "ROUTE: insult"
    assert result.input_tokens == 12
    assert result.output_tokens == 3
    # Real provenance from the door, not an echo of the request.
    assert result.model == "claude-haiku-4-5-20251001"
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_model_falls_back_to_the_requested_one(patched, monkeypatch):
    """A door that reports no model must not blank the telemetry field."""

    class _NoModelRunner(_FakeRunner):
        async def run(self, _prompt: str) -> _FakeResult:
            result = _FakeResult()
            result.model = None
            return result

    monkeypatch.setattr(host_llm, "Runner", _NoModelRunner)
    client = host_llm.HostRouterLLM()
    result = await client.complete("Route this.", "x")
    assert result.model == host_llm.DEFAULT_MODEL


@pytest.mark.asyncio
async def test_router_runs_with_no_guards(patched):
    """The host has no character to protect — NO anti-drift guard, ever."""
    client = host_llm.HostRouterLLM()
    await client.complete("Route this.", "x")
    assert _FakeRunner.last_kwargs.get("guards") == []
    # The instruction is passed as the runner persona slot (operational prompt),
    # not a baked-in character.
    assert _FakeRunner.last_kwargs.get("persona") == "Route this."


def test_router_addresses_its_own_casita_in_complete_mode(patched):
    """The host's casita is never a persona's, and a one-word classification
    asks the door for no tools and no builtins."""
    host_llm.HostRouterLLM()
    assert _FakeBackend.last_kwargs["project"] == host_llm.DEFAULT_PROJECT
    assert _FakeBackend.last_kwargs["default_mode"] == "complete"
    assert _FakeBackend.last_kwargs["default_model"] == host_llm.DEFAULT_MODEL


def test_casita_and_model_are_env_overridable(patched, monkeypatch):
    monkeypatch.setenv("HOST_ROUTER_PROJECT", "demux-canary")
    monkeypatch.setenv("HOST_ROUTER_MODEL", "sonnet")
    client = host_llm.HostRouterLLM()
    assert client.project == "demux-canary"
    assert _FakeBackend.last_kwargs["project"] == "demux-canary"
    assert _FakeBackend.last_kwargs["default_model"] == "sonnet"


@pytest.mark.asyncio
async def test_aclose_drains_the_pooled_door_client(patched):
    """AIREBackend holds a pooled httpx.AsyncClient; a door client nobody closes
    leaks its connections past shutdown (the aire_route lesson)."""
    closed: list[bool] = []

    async def _aclose() -> None:
        closed.append(True)

    client = host_llm.HostRouterLLM()
    client._backend.aclose = _aclose  # type: ignore[method-assign]
    await client.aclose()
    assert closed == [True]
