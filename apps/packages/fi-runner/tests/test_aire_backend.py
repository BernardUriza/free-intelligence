"""AIREBackend — the persistent-server backend (HTTP client of AIRE).

These tests never touch the network: they feed canned AIRE SSE events through the
mapping layer and assert the fi-runner event/result contract. The live E2E turn
against the real door is exercised out-of-band (a real turn spends real tokens).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fi_runner import AIREBackend, ToolPolicy
from fi_runner.backend import AgentBackend, BackendError, MCPServerSpec, TurnImage


def _backend() -> AIREBackend:
    return AIREBackend(project="test_casita", gate_url="https://gate.example", auth_token="tok")


def test_is_agent_backend() -> None:
    assert isinstance(_backend(), AgentBackend)
    assert hasattr(_backend(), "run_turn_stream")


def test_requires_door_config() -> None:
    b = AIREBackend(project="p", gate_url="", auth_token="")
    with pytest.raises(BackendError, match="door not configured"):
        b._require_door()


def test_turn_tools_unions_registry_and_specs_deduped() -> None:
    b = AIREBackend(
        project="p", gate_url="https://g", auth_token="t", registry_tools=("memory",)
    )
    specs = [
        MCPServerSpec(name="memory", command="python", args=["-m", "memory"]),
        MCPServerSpec(name="rag", command="python", args=["-m", "rag"]),
    ]
    assert b._turn_tools(specs) == ["memory", "rag"]


def test_maps_result_event() -> None:
    b = _backend()
    tr = b._to_result(
        {
            "text": "hola",
            "usage": {"total_cost_usd": 0.01},
            "session_id": "sid-1",
            "model": "claude-haiku-4-5-20251001",
            "tool_calls": [{"name": "mcp__rag__search", "id": "t1"}],
        },
        session="fallback",
    )
    assert tr.text == "hola"
    assert tr.session_id == "sid-1"
    assert tr.usage == {"total_cost_usd": 0.01}
    assert tr.model == "claude-haiku-4-5-20251001"  # real provenance off the result event
    assert len(tr.tool_calls) == 1
    assert tr.tool_calls[0].server == "rag"  # ToolCall.make parsed the mcp server


def test_result_without_model_stays_none() -> None:
    tr = _backend()._to_result({"text": "x"}, session="s")
    assert tr.model is None


def test_result_session_falls_back_when_absent() -> None:
    tr = _backend()._to_result({"text": "x"}, session="fallback-sid")
    assert tr.session_id == "fallback-sid"


@pytest.mark.asyncio
async def test_stream_maps_aire_events_to_fi_events(monkeypatch: Any) -> None:
    """AIRE's text/tool_call/result events become fi-runner's stream vocabulary."""
    b = _backend()

    async def fake_stream(project: str, session: str, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "text", "text": "hel"}
        yield {"type": "text", "text": "lo"}
        yield {"type": "tool_call", "tool": {"name": "mcp__db__q", "id": "t1"}}
        yield {"type": "result", "result": {"text": "hello", "session_id": "sid-9"}}
        yield {"type": "done", "session": session}

    monkeypatch.setattr(b, "_stream_events", fake_stream)
    monkeypatch.setattr(b, "_ensure_prompt", _anoop)

    events = []
    async for ev in b.run_turn_stream(
        system_prompt="",
        user_message="hi",
        mcp_servers=[],
        tool_policy=ToolPolicy(),
        session_id="s",
    ):
        events.append(ev)

    assert [e["type"] for e in events] == ["text", "text", "tool_call", "result"]
    assert events[2]["tool"].server == "db"
    assert events[3]["result"].text == "hello"
    assert events[3]["result"].session_id == "sid-9"


@pytest.mark.asyncio
async def test_forwards_model_images_and_tools_in_body(monkeypatch: Any) -> None:
    """The three former reject clauses now ride the body: model, images, and
    per-turn mcp_servers translated to registry names — in the configured mode
    (the door runs registry tools in complete since aire-server 5ae8e33)."""
    b = _backend()
    seen: dict[str, Any] = {}

    async def fake_stream(project: str, session: str, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        seen.update(body)
        yield {"type": "result", "result": {"text": "ok"}}

    monkeypatch.setattr(b, "_stream_events", fake_stream)
    monkeypatch.setattr(b, "_ensure_prompt", _anoop)
    async for _ in b.run_turn_stream(
        system_prompt="",
        user_message="what color?",
        mcp_servers=[MCPServerSpec(name="memory", command="python", args=["-m", "m"])],
        tool_policy=ToolPolicy(),
        model="haiku",
        session_id="s",
        images=[TurnImage(media_type="image/png", data="aGk=")],
    ):
        pass

    assert seen["mode"] == "complete"  # tools no longer force agent (5ae8e33)
    assert seen["tools"] == ["memory"]
    assert seen["model"] == "haiku"
    assert seen["images"] == [{"media_type": "image/png", "data": "aGk="}]


@pytest.mark.asyncio
async def test_text_turn_body_omits_optional_fields(monkeypatch: Any) -> None:
    """A plain text turn sends exactly {mode, message} — no None-noise keys."""
    b = _backend()
    seen: dict[str, Any] = {}

    async def fake_stream(project: str, session: str, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        seen.update(body)
        yield {"type": "result", "result": {"text": "ok"}}

    monkeypatch.setattr(b, "_stream_events", fake_stream)
    monkeypatch.setattr(b, "_ensure_prompt", _anoop)
    async for _ in b.run_turn_stream(
        system_prompt="",
        user_message="hi",
        mcp_servers=[],
        tool_policy=ToolPolicy(),
        session_id="s",
    ):
        pass
    assert seen == {"mode": "complete", "message": "hi"}


@pytest.mark.asyncio
async def test_error_event_raises(monkeypatch: Any) -> None:
    b = _backend()

    async def fake_stream(project: str, session: str, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "error", "error": "budget_exhausted", "detail": "cut"}

    monkeypatch.setattr(b, "_stream_events", fake_stream)
    monkeypatch.setattr(b, "_ensure_prompt", _anoop)

    with pytest.raises(BackendError, match="budget_exhausted"):
        async for _ in b.run_turn_stream(
            system_prompt="",
            user_message="hi",
            mcp_servers=[],
            tool_policy=ToolPolicy(),
            session_id="s",
        ):
            pass


@pytest.mark.asyncio
async def test_run_turn_raises_on_no_result(monkeypatch: Any) -> None:
    """A stream that never yields a result is a real failure, not empty success."""
    b = _backend()

    async def fake_stream(project: str, session: str, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "text", "text": "partial"}

    monkeypatch.setattr(b, "_stream_events", fake_stream)
    monkeypatch.setattr(b, "_ensure_prompt", _anoop)

    with pytest.raises(BackendError, match="no result event"):
        await b.run_turn(
            system_prompt="",
            user_message="hi",
            mcp_servers=[],
            tool_policy=ToolPolicy(),
            session_id="s",
        )


@pytest.mark.asyncio
async def test_registry_tools_ride_the_configured_mode(monkeypatch: Any) -> None:
    """Registry tools ride the body in the configured mode — no agent forcing:
    the door runs them in complete (aire-server 5ae8e33), and agent mode would
    drag in preset builtins (Read/Write/WebSearch…) nobody asked for."""
    b = AIREBackend(
        project="p", gate_url="https://g", auth_token="t", registry_tools=("memory",)
    )
    seen: dict[str, Any] = {}

    async def fake_stream(project: str, session: str, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        seen.update(body)
        yield {"type": "result", "result": {"text": "ok"}}

    monkeypatch.setattr(b, "_stream_events", fake_stream)
    monkeypatch.setattr(b, "_ensure_prompt", _anoop)
    async for _ in b.run_turn_stream(
        system_prompt="",
        user_message="hi",
        mcp_servers=[],
        tool_policy=ToolPolicy(),
        session_id="s",
    ):
        pass
    assert seen["mode"] == "complete"
    assert seen["tools"] == ["memory"]


@pytest.mark.asyncio
async def test_no_registry_tools_keeps_default_mode(monkeypatch: Any) -> None:
    b = AIREBackend(
        project="p", gate_url="https://g", auth_token="t", default_mode="complete"
    )
    seen: dict[str, Any] = {}

    async def fake_stream(project: str, session: str, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        seen.update(body)
        yield {"type": "result", "result": {"text": "ok"}}

    monkeypatch.setattr(b, "_stream_events", fake_stream)
    monkeypatch.setattr(b, "_ensure_prompt", _anoop)
    async for _ in b.run_turn_stream(
        system_prompt="",
        user_message="hi",
        mcp_servers=[],
        tool_policy=ToolPolicy(),
        session_id="s",
    ):
        pass
    assert seen["mode"] == "complete"


@pytest.mark.asyncio
async def test_per_turn_project_override_routes_the_casita(monkeypatch: Any) -> None:
    """OG118-LIVING-CLAUDE: a wired ``project_for_turn`` resolver overrides the
    fixed project per turn (casita-per-chat); a None/empty answer falls back."""
    current: dict[str, str | None] = {"project": "og118-chat-1"}
    b = AIREBackend(
        project="og118",
        gate_url="https://g",
        auth_token="t",
        project_for_turn=lambda: current["project"],
    )
    seen: list[str] = []

    async def fake_stream(project: str, session: str, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        seen.append(project)
        yield {"type": "result", "result": {"text": "ok"}}

    monkeypatch.setattr(b, "_stream_events", fake_stream)
    monkeypatch.setattr(b, "_ensure_prompt", _anoop)
    async for _ in b.run_turn_stream(
        system_prompt="", user_message="hi", mcp_servers=[], tool_policy=ToolPolicy()
    ):
        pass
    current["project"] = None
    async for _ in b.run_turn_stream(
        system_prompt="", user_message="hi", mcp_servers=[], tool_policy=ToolPolicy()
    ):
        pass
    assert seen == ["og118-chat-1", "og118"]


class _PostRecorder:
    """Stands in for the lazy httpx client: records /init POSTs, answers 200."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def post(self, url: str, *, headers: Any = None, json: Any = None) -> Any:
        self.calls.append((url, json))

        class _Res:
            status_code = 200
            text = "ok"

        return _Res()


@pytest.mark.asyncio
async def test_ensure_prompt_inits_once_per_casita() -> None:
    """Init state is tracked PER project: the same prompt re-inits nothing, a new
    casita gets its own /init (the first turn of a chat installs the base)."""
    b = _backend()
    rec = _PostRecorder()
    b._client = rec
    await b._ensure_prompt("og118-chat-1", "base persona")
    await b._ensure_prompt("og118-chat-1", "base persona")
    await b._ensure_prompt("og118-chat-2", "base persona")
    urls = [u for u, _ in rec.calls]
    assert urls == [
        "https://gate.example/projects/og118-chat-1/init",
        "https://gate.example/projects/og118-chat-2/init",
    ]
    assert all(body == {"claude_md": "base persona"} for _, body in rec.calls)


async def _anoop(*args: Any, **kwargs: Any) -> None:
    return None
