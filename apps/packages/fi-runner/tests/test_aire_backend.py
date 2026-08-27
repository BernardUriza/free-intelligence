"""AIREBackend — the persistent-server backend (HTTP client of AIRE).

These tests never touch the network: they feed canned AIRE SSE events through the
mapping layer and assert the fi-runner event/result contract. The live E2E turn
against the real door is exercised out-of-band (a real turn spends real tokens).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fi_runner import AIREBackend, AIREDoorError, ToolPolicy
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

    with pytest.raises(AIREDoorError, match="budget_exhausted") as exc_info:
        async for _ in b.run_turn_stream(
            system_prompt="",
            user_message="hi",
            mcp_servers=[],
            tool_policy=ToolPolicy(),
            session_id="s",
        ):
            pass
    # The code rides as DATA: consumers classify terminal-vs-backpressure on it,
    # never on the message wording. And it stays a BackendError, so nothing
    # upstream needs to know the subclass exists.
    assert exc_info.value.code == "budget_exhausted"
    assert isinstance(exc_info.value, BackendError)


class _FakeSSEStream:
    """An httpx-shaped streaming response: enough surface for _stream_events."""

    def __init__(self, status_code: int, lines: list[str], body: bytes = b"") -> None:
        self.status_code = status_code
        self._lines = lines
        self._body = body

    async def __aenter__(self) -> "_FakeSSEStream":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None

    async def aread(self) -> bytes:
        return self._body

    async def aiter_lines(self) -> AsyncIterator[str]:
        for line in self._lines:
            yield line


class _FakeStreamHTTP:
    def __init__(self, response: _FakeSSEStream) -> None:
        self._response = response

    def stream(self, *args: Any, **kwargs: Any) -> _FakeSSEStream:
        return self._response


@pytest.mark.asyncio
async def test_typeless_error_payload_is_normalized_to_an_error_event() -> None:
    """AIRE's edge yields budget_exceeded / slot_busy payloads WITHOUT a "type"
    key (messages.py emits them from except-clauses). Dropping them would kill
    the turn later as a bare "no result event" — the code must survive."""
    b = _backend()
    b._http = lambda: _FakeStreamHTTP(  # type: ignore[method-assign]
        _FakeSSEStream(200, ['data: {"error": "slot_busy", "detail": "pool full"}'])
    )
    events = [ev async for ev in b._stream_events("p", "s", {})]
    assert events == [{"type": "error", "error": "slot_busy", "detail": "pool full"}]


@pytest.mark.asyncio
async def test_http_door_failure_keeps_the_status_as_data() -> None:
    b = _backend()
    b._http = lambda: _FakeStreamHTTP(  # type: ignore[method-assign]
        _FakeSSEStream(503, [], body=b"busy")
    )
    with pytest.raises(AIREDoorError, match="AIRE door 503") as exc_info:
        async for _ in b._stream_events("p", "s", {}):
            pass
    assert exc_info.value.http_status == 503
    assert exc_info.value.code is None


@pytest.mark.asyncio
async def test_a_budget_cut_after_the_result_keeps_the_answer(monkeypatch: Any) -> None:
    """AIRE emits the #23 cut AFTER the result event, as a footnote saying the
    spent client was retired. Raising over it throws a finished answer away
    (discord-bot's 2026-08-26 P1: the channel stuck on a neutral "…"). The
    answer wins; the retired client rebuilds on the next turn."""
    b = _backend()

    async def fake_stream(project: str, session: str, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "result", "result": {"text": "hola", "session_id": "sid-1"}}
        yield {"type": "error", "error": "budget_exhausted", "detail": "ceiling reached"}

    monkeypatch.setattr(b, "_stream_events", fake_stream)
    monkeypatch.setattr(b, "_ensure_prompt", _anoop)

    result = await b.run_turn(
        system_prompt="", user_message="m", mcp_servers=[], tool_policy=ToolPolicy(), session_id="s"
    )
    assert result.text == "hola", "a budget footnote voided a delivered answer"


@pytest.mark.asyncio
async def test_a_budget_cut_with_no_answer_stays_an_error(monkeypatch: Any) -> None:
    """Only a result IN HAND survives the cut: with nothing to deliver, the
    error must surface so the caller's resend can continue the work."""
    b = _backend()

    async def fake_stream(project: str, session: str, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "error", "error": "budget_exhausted", "detail": "cut"}

    monkeypatch.setattr(b, "_stream_events", fake_stream)
    monkeypatch.setattr(b, "_ensure_prompt", _anoop)

    with pytest.raises(AIREDoorError, match="budget_exhausted"):
        await b.run_turn(
            system_prompt="", user_message="m", mcp_servers=[], tool_policy=ToolPolicy(), session_id="s"
        )


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
async def test_thin_birth_base_holds_the_persona_chats_get_the_stub() -> None:
    """THIN BIRTH (aire-server ef21e68): the full persona is installed ONCE in
    the shared base casita — FIRST, so a chat's first spawn finds it — and each
    chat casita is born with only the ``@base`` stub. Repeats re-init nothing;
    a second chat adds only its own stub."""
    b = _backend()
    rec = _PostRecorder()
    b._client = rec
    await b._ensure_prompt("og118-chat-1", "base persona")
    await b._ensure_prompt("og118-chat-1", "base persona")
    await b._ensure_prompt("og118-chat-2", "base persona")
    assert rec.calls == [
        ("https://gate.example/projects/test_casita/init", {"claude_md": "base persona"}),
        ("https://gate.example/projects/og118-chat-1/init", {"claude_md": "@base test_casita"}),
        ("https://gate.example/projects/og118-chat-2/init", {"claude_md": "@base test_casita"}),
    ]


@pytest.mark.asyncio
async def test_turn_on_the_base_casita_itself_gets_the_full_prompt() -> None:
    """A turn resolving to the fixed project (no chat override) installs the
    persona there and never writes a self-referential stub."""
    b = _backend()
    rec = _PostRecorder()
    b._client = rec
    await b._ensure_prompt("test_casita", "base persona")
    assert rec.calls == [
        ("https://gate.example/projects/test_casita/init", {"claude_md": "base persona"}),
    ]


@pytest.mark.asyncio
async def test_process_restart_rebases_a_fat_born_chat_to_the_stub() -> None:
    """The init cache is per PROCESS: a fresh backend (= restarted process)
    re-inits a pre-thin-birth chat casita with the stub — AIRE's rebase swaps
    its frozen persona copy for ``@base`` while preserving its living part."""
    fat = _backend()
    rec = _PostRecorder()
    fat._client = rec
    fat._inited_prompts["og118-chat-old"] = "a frozen 4KB persona copy"
    restarted = _backend()
    restarted._client = rec
    await restarted._ensure_prompt("og118-chat-old", "base persona")
    assert rec.calls == [
        ("https://gate.example/projects/test_casita/init", {"claude_md": "base persona"}),
        ("https://gate.example/projects/og118-chat-old/init", {"claude_md": "@base test_casita"}),
    ]


async def _anoop(*args: Any, **kwargs: Any) -> None:
    return None


# --- native memory: the probe that ends the double-memory ---------------------
# AIRE owns the transcript, so the Runner must RESUME it instead of replaying the
# client's history into a throwaway session. That decision hangs on two members;
# these pin them, including the degrade path (a door that cannot answer must fall
# back to the old replay cost, never to a wrong resume).


class _FakeResponse:
    def __init__(self, status_code: int, payload: Any = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class _FakeHTTP:
    def __init__(self, response: Any = None, boom: Exception | None = None) -> None:
        self.response = response
        self.boom = boom
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def get(self, url: str, headers: dict[str, str]) -> Any:
        self.calls.append((url, headers))
        if self.boom is not None:
            raise self.boom
        return self.response


def _with_http(b: AIREBackend, http: _FakeHTTP) -> AIREBackend:
    b._http = lambda: http  # type: ignore[method-assign]
    return b


def test_durable_memory_is_not_configurable() -> None:
    """AIRE's store IS this backend's memory; there is no wiring in which it
    remembers less. The local host derives the same flag from its session_store."""
    assert _backend().has_durable_memory is True


@pytest.mark.asyncio
async def test_has_session_asks_the_door_about_the_casita_this_turn_addresses() -> None:
    b = AIREBackend(
        project="og118",
        gate_url="https://gate.example",
        auth_token="tok",
        project_for_turn=lambda: "og118-chat-7",
    )
    http = _FakeHTTP(_FakeResponse(200, {"session": "chat-7", "exists": True}))
    _with_http(b, http)
    assert await b.has_session("chat-7") is True
    url, headers = http.calls[0]
    assert url == "https://gate.example/projects/og118-chat-7/sessions/chat-7"
    assert headers["Authorization"] == "Bearer tok"


@pytest.mark.asyncio
async def test_a_session_the_door_does_not_know_is_absent() -> None:
    b = _with_http(_backend(), _FakeHTTP(_FakeResponse(200, {"exists": False})))
    assert await b.has_session("nope") is False


@pytest.mark.asyncio
async def test_an_older_door_without_the_route_degrades_to_replay() -> None:
    """A 404 means this AIRE predates the route. Answering False makes the Runner
    replay — the exact behavior it had before this method existed."""
    b = _with_http(_backend(), _FakeHTTP(_FakeResponse(404, None)))
    assert await b.has_session("s") is False


@pytest.mark.asyncio
async def test_an_unreachable_door_degrades_instead_of_raising() -> None:
    """A probe failure must not kill a turn that would otherwise run fine on
    replay. The cost regresses; the turn does not die."""
    b = _with_http(_backend(), _FakeHTTP(boom=OSError("connection refused")))
    assert await b.has_session("s") is False


@pytest.mark.asyncio
async def test_an_unconfigured_door_is_still_a_loud_failure() -> None:
    """Degrading covers a door that answers badly, never one that was never set:
    that is a misconfiguration and stays as loud here as it is on a turn."""
    b = AIREBackend(project="p", gate_url="", auth_token="")
    with pytest.raises(BackendError, match="door not configured"):
        await b.has_session("s")


# --- the glass box works on this door too ------------------------------------
# AIRE ships the same task_tracker tool names under its own server name
# (aire-server #45). The plan events are derived from tool CALLS, so the only
# thing that had to change is which server names count as a plan.


def test_the_translator_reads_aires_tracker_as_well_as_fi_cores() -> None:
    from fi_runner._plan_events import _derive_plan_events
    from fi_runner.backend import ToolCall

    for server, name in (("task_tracker", "mcp__task_tracker__declare_plan"),
                         ("fi_core_task_tracker", "mcp__fi_core_task_tracker__declare_plan")):
        call = ToolCall.make(name, input={"steps": ["buscar", "responder"]})
        assert call.server == server
        events = _derive_plan_events(call, session_id="s", request_id="r")
        assert [e["type"] for e in events] == ["plan"], f"{server} left the glass box dark"
        assert events[0]["data"]["steps"] == ["buscar", "responder"]


def test_a_tool_from_some_other_server_is_not_a_plan() -> None:
    from fi_runner._plan_events import _derive_plan_events
    from fi_runner.backend import ToolCall

    call = ToolCall.make("mcp__persona__update", input={"living": "x"})
    assert _derive_plan_events(call, session_id="s", request_id="r") == []
