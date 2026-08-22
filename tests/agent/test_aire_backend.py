"""The vendored AIRE door client — the wire contract, without touching the wire.

`aire_backend.py` is a vendored copy of fi-runner's canonical client (it dies the
day a fi-runner carrying it reaches the conda channel). What is asserted here is
only what THIS repo depends on and what the four vendoring adaptations changed:
thin birth, the tools field, the model field, and the type-less error payloads
AIRE's edge really emits.
"""

from __future__ import annotations

import json

import pytest

from persona_runner.engine.aire_backend import AIREBackend, BackendError, ToolPolicy


class _Response:
    def __init__(self, status_code=200, text="", lines=()):
        self.status_code = status_code
        self.text = text
        self._lines = list(lines)

    async def aread(self):
        return self.text.encode()

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeHTTP:
    """Records every call so the door's REQUEST shape can be asserted."""

    def __init__(self, lines=(), post_status=200):
        self.posts: list[tuple[str, dict]] = []
        self.streams: list[tuple[str, dict]] = []
        self._lines = lines
        self._post_status = post_status

    async def post(self, url, headers=None, json=None):
        self.posts.append((url, json or {}))
        return _Response(status_code=self._post_status, text="nope")

    def stream(self, _method, url, headers=None, json=None):
        self.streams.append((url, json or {}))
        return _Response(lines=self._lines)


def _sse(*events):
    return [f"data: {json.dumps(ev)}" for ev in events]


_RESULT = {"type": "result", "result": {"text": "hola", "usage": {"input_tokens": 3}, "model": "claude-x"}}


def _backend(http, **kw):
    kw.setdefault("gate_url", "https://gate.example.test")
    kw.setdefault("auth_token", "t")
    backend = AIREBackend("insult", **kw)
    backend._client = http
    return backend


@pytest.mark.asyncio
async def test_the_door_refuses_to_run_unconfigured():
    """No gate/token is an honest error, never a call to a dead default."""
    backend = AIREBackend("insult", gate_url="", auth_token="")
    with pytest.raises(BackendError, match="not configured"):
        await backend.run_turn(system_prompt="p", user_message="m", mcp_servers=[], tool_policy=ToolPolicy())


@pytest.mark.asyncio
async def test_thin_birth_inits_the_base_casita_first_then_the_chat_stub():
    """The FULL persona lands in the base; the chat casita gets only `@base`, in
    that order, so a chat's first spawn already finds a persona to dereference."""
    http = _FakeHTTP(lines=_sse(_RESULT))
    backend = _backend(http, project_for_turn=lambda: "insult-555")

    await backend.run_turn(system_prompt="EL ADN COMPLETO", user_message="m", mcp_servers=[], tool_policy=ToolPolicy())

    assert [url for url, _ in http.posts] == [
        "https://gate.example.test/projects/insult/init",
        "https://gate.example.test/projects/insult-555/init",
    ]
    assert http.posts[0][1]["claude_md"] == "EL ADN COMPLETO"
    assert http.posts[1][1]["claude_md"] == "@base insult"


@pytest.mark.asyncio
async def test_the_turn_is_posted_to_the_per_chat_casita_not_the_base():
    """The base holds the DNA; the conversation lives in the chat casita."""
    http = _FakeHTTP(lines=_sse(_RESULT))
    backend = _backend(http, project_for_turn=lambda: "insult-555")

    await backend.run_turn(
        system_prompt="dna", user_message="m", mcp_servers=[], tool_policy=ToolPolicy(), session_id="live"
    )

    url, _ = http.streams[0]
    assert url == "https://gate.example.test/projects/insult-555/sessions/live/messages"


@pytest.mark.asyncio
async def test_an_unchanged_prompt_is_not_re_inited():
    """/init is idempotent per process — re-writing the same prompt is wasted I/O."""
    http = _FakeHTTP(lines=_sse(_RESULT, _RESULT))
    backend = _backend(http)

    for _ in range(2):
        await backend.run_turn(system_prompt="dna", user_message="m", mcp_servers=[], tool_policy=ToolPolicy())

    assert len(http.posts) == 1


@pytest.mark.asyncio
async def test_a_failed_init_surfaces_instead_of_running_a_persona_less_turn():
    """A casita without its DNA would answer out of character — that is an error."""
    http = _FakeHTTP(lines=_sse(_RESULT), post_status=500)
    backend = _backend(http)
    with pytest.raises(BackendError, match="AIRE init 500"):
        await backend.run_turn(system_prompt="dna", user_message="m", mcp_servers=[], tool_policy=ToolPolicy())


@pytest.mark.asyncio
async def test_registry_tools_and_the_model_ride_the_turn_body():
    """`tools` + `model` are the two per-turn fields stage 2 depends on (#29)."""
    http = _FakeHTTP(lines=_sse(_RESULT))
    backend = _backend(http, registry_tools=("persona", "memory"), default_mode="agent")

    await backend.run_turn(
        system_prompt="",
        user_message="m",
        mcp_servers=[],
        tool_policy=ToolPolicy(),
        model="claude-sonnet-4-6",
    )

    _, body = http.streams[0]
    assert body["tools"] == ["persona", "memory"]
    assert body["model"] == "claude-sonnet-4-6"
    assert body["mode"] == "agent"


@pytest.mark.asyncio
async def test_a_type_less_budget_payload_becomes_an_error_not_a_torn_stream():
    """AIRE's edge yields `budget_exceeded` WITHOUT a `type` key (messages.py
    except-clauses). Upstream drops it and dies as a bare "no result event";
    the vendored adaptation keeps the CODE the neutral error path needs."""
    http = _FakeHTTP(lines=_sse({"error": "budget_exceeded", "detail": "ceiling hit"}))
    backend = _backend(http)

    with pytest.raises(BackendError, match="budget_exceeded"):
        await backend.run_turn(system_prompt="", user_message="m", mcp_servers=[], tool_policy=ToolPolicy())


@pytest.mark.asyncio
async def test_a_type_less_slot_busy_payload_keeps_its_code():
    """Backpressure must stay distinguishable from a terminal cut."""
    http = _FakeHTTP(lines=_sse({"error": "slot_busy", "detail": "all 2 slots busy"}))
    backend = _backend(http)

    with pytest.raises(BackendError, match="slot_busy"):
        await backend.run_turn(system_prompt="", user_message="m", mcp_servers=[], tool_policy=ToolPolicy())


@pytest.mark.asyncio
async def test_a_stream_with_no_result_event_is_a_failure_not_an_empty_success():
    """Art. 2 at the wire: a torn stream never returns a blank happy answer."""
    http = _FakeHTTP(lines=_sse({"type": "text", "text": "media frase"}, {"type": "done"}))
    backend = _backend(http)

    with pytest.raises(BackendError, match="no result event"):
        await backend.run_turn(system_prompt="", user_message="m", mcp_servers=[], tool_policy=ToolPolicy())


@pytest.mark.asyncio
async def test_the_result_carries_aires_own_model_provenance():
    """`model` is read off the assistant messages by AIRE — the model that
    ANSWERED, which is what makes the divergence check possible at all."""
    http = _FakeHTTP(lines=_sse(_RESULT))
    backend = _backend(http)

    result = await backend.run_turn(system_prompt="", user_message="m", mcp_servers=[], tool_policy=ToolPolicy())

    assert result.model == "claude-x"
    assert result.text == "hola"


def test_turn_tools_dedupes_while_keeping_order():
    """Only NAMES cross the wire, deduped — the door mounts its own servers."""
    backend = AIREBackend("insult", registry_tools=("persona", "memory"))

    class _Spec:
        name = "memory"

    assert backend._turn_tools([_Spec()]) == ["persona", "memory"]
