"""PR-4b — HostRouterLLM unit test (no network).

Verifies the demux host's gpt-4.1 reception brain maps an instruction + input
onto fi_runner and reads back a token-accounted result, with NO persona/guard
machinery (the host is a router, not a character). fi_runner is mocked so CI
never touches Azure.
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


class _FakeRunner:
    last_kwargs: ClassVar[dict] = {}

    def __init__(self, **kwargs) -> None:
        _FakeRunner.last_kwargs = kwargs

    async def run(self, _prompt: str) -> _FakeResult:
        return _FakeResult()


class _FakeBackend:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


@pytest.fixture
def patched(monkeypatch):
    monkeypatch.setattr(host_llm, "CodexBackend", _FakeBackend)
    monkeypatch.setattr(host_llm, "Runner", _FakeRunner)
    monkeypatch.setenv("AZURE_OPENAI_KEY", "k")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://insult-openai.example/")
    monkeypatch.setenv("AZURE_OPENAI_GPT_DEPLOYMENT", "gpt-4.1")


@pytest.mark.asyncio
async def test_complete_returns_token_accounted_result(patched):
    client = host_llm.HostRouterLLM()
    result = await client.complete("Classify the target persona.", "hola")
    assert result.text == "ROUTE: insult"
    assert result.input_tokens == 12
    assert result.output_tokens == 3
    assert result.model == "gpt-4.1"
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_router_runs_with_no_guards(patched):
    """The host has no character to protect — NO anti-drift guard, ever."""
    client = host_llm.HostRouterLLM()
    await client.complete("Route this.", "x")
    assert _FakeRunner.last_kwargs.get("guards") == []
    # The instruction is passed as the runner persona slot (operational prompt),
    # not a baked-in character.
    assert _FakeRunner.last_kwargs.get("persona") == "Route this."


def test_endpoint_trailing_slash_stripped(patched):
    client = host_llm.HostRouterLLM(endpoint="https://x.example/")
    assert client.endpoint == "https://x.example"
