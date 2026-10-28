"""external_engine — the external_http_engine proxy on the engine's TICKET
(ENGINE-BINDING-ADR-1, OG118-EXTERNAL-TURN-1).

The turn is `POST /v1/turn/jobs` + the `events` tail + the result poll. These
cover the payload contract the engine depends on, the failure branches (not
configured, transport error, non-202, empty body, lost ticket), the live
`tool_call` frames arriving BEFORE the answer, the idempotent job id, the
deferred release and its late delivery — and the hard invariant that the bearer
token NEVER reaches a client-facing error message.
"""

from __future__ import annotations

import asyncio
import contextlib
import json

import httpx
import pytest

import external_engine


class _FakeResp:
    def __init__(self, status: int, payload: object) -> None:
        self.status_code = status
        self._payload = payload

    def json(self) -> object:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _done(data: dict) -> _FakeResp:
    return _FakeResp(200, {"job_id": "j1", "status": "done", "response": data})


def _running() -> _FakeResp:
    return _FakeResp(200, {"job_id": "j1", "status": "running"})


def _sse(event_id: int | None, frame: dict, event: str | None = None) -> list[str]:
    head = ([f"id: {event_id}"] if event_id is not None else []) + ([f"event: {event}"] if event else [])
    return [*head, f"data: {json.dumps(frame)}", ""]


DONE_LINES = _sse(None, {}, "done")


class _FakeStream:
    def __init__(self, status: int, lines: list[str]) -> None:
        self.status_code = status
        self._lines = lines

    async def aiter_lines(self):
        for line in self._lines:
            yield line


def _runner(
    data: dict | None = None,
    *,
    post: _FakeResp | None = None,
    polls: list[_FakeResp] | None = None,
    poll_delay_s: float = 0.0,
    events: list[str] | None = None,
    events_status: int = 200,
    raise_exc: Exception | None = None,
    sent: dict | None = None,
    seen: dict | None = None,
):
    """`httpx.AsyncClient` as the ticket runner: `post` opens the job, `stream`
    serves the event log, `get` answers the poll (the last entry repeats)."""
    poll_queue = list(polls) if polls is not None else [_done(data if data is not None else {"text": "ok"})]
    event_lines = list(events) if events is not None else DONE_LINES
    seen = seen if seen is not None else {}
    seen.setdefault("polls", 0)
    seen.setdefault("event_headers", [])

    class _FakeClient:
        def __init__(self, *a, **k) -> None: ...

        async def aclose(self) -> None:
            seen["closed"] = True

        async def post(self, url, json, headers):
            seen["post_url"] = url
            if sent is not None:
                sent.update(json)
            if raise_exc is not None:
                raise raise_exc
            return post or _FakeResp(202, {"job_id": "j1"})

        async def get(self, url, params, headers):
            seen["polls"] += 1
            seen["poll_url"] = url
            seen["wait_s"] = params.get("wait_s")
            if poll_delay_s:
                await asyncio.sleep(poll_delay_s)
            return poll_queue.pop(0) if len(poll_queue) > 1 else poll_queue[0]

        @contextlib.asynccontextmanager
        async def stream(self, method, url, headers, timeout):
            seen["event_headers"].append(headers)
            yield _FakeStream(events_status, event_lines)

    return _FakeClient


async def _collect(agen) -> list[dict]:
    return [ev async for ev in agen]


def _configure(monkeypatch, *, url="https://engine.example", token="SECRET-TOKEN-XYZ"):
    monkeypatch.setattr(external_engine, "RUNNER_URL", url)
    monkeypatch.setattr(external_engine, "RUNNER_TOKEN", token)


def _turn(**overrides):
    kwargs = dict(persona_id="vultur", user_text="hi", session_uuid="s", user_id="u")
    kwargs.update(overrides)
    return external_engine.stream_external_turn(**kwargs)


def _install(monkeypatch, client_cls) -> None:
    monkeypatch.setattr(external_engine.httpx, "AsyncClient", client_cls)


@pytest.mark.asyncio
async def test_unconfigured_yields_clean_error(monkeypatch) -> None:
    _configure(monkeypatch, url="", token="")
    evs = await _collect(_turn())
    assert evs == [{"type": "error", "message": "external engine not configured (OG118_EXTERNAL_RUNNER_URL/TOKEN unset)"}]


@pytest.mark.asyncio
async def test_happy_path_yields_text_then_result_with_model(monkeypatch) -> None:
    """The answer AND its provenance: the engine reports which model ran, and the
    turn settles with a `result` carrying it — the same shape the local runner
    emits, so the client renders the model chip on both routes."""
    _configure(monkeypatch)
    seen: dict = {}
    _install(monkeypatch, _runner({"text": "  Soy Vultur.  ", "model": "claude-sonnet-4-6"}, seen=seen))
    evs = await _collect(_turn())
    assert evs == [
        {"type": "text", "text": "Soy Vultur."},
        {"type": "result", "result": {"text": "Soy Vultur.", "model": "claude-sonnet-4-6"}},
    ]
    assert seen["post_url"].endswith("/v1/turn/jobs")
    assert seen["poll_url"].endswith("/v1/turn/jobs/j1")
    assert seen["wait_s"] == external_engine.POLL_WAIT_S
    assert seen["closed"] is True


@pytest.mark.asyncio
async def test_result_model_is_none_when_the_engine_does_not_report_one(monkeypatch) -> None:
    _configure(monkeypatch)
    _install(monkeypatch, _runner({"text": "hola"}))
    evs = await _collect(_turn())
    assert evs[-1] == {"type": "result", "result": {"text": "hola", "model": None}}


@pytest.mark.asyncio
async def test_transport_error_is_secret_free(monkeypatch) -> None:
    _configure(monkeypatch, token="SECRET-TOKEN-XYZ")
    _install(monkeypatch, _runner(raise_exc=httpx.ConnectError("boom")))
    evs = await _collect(_turn())
    assert len(evs) == 1 and evs[0]["type"] == "error"
    assert "unreachable" in evs[0]["message"]
    assert "SECRET-TOKEN-XYZ" not in evs[0]["message"]


@pytest.mark.asyncio
async def test_a_refused_ticket_reports_status_not_token(monkeypatch) -> None:
    _configure(monkeypatch, token="SECRET-TOKEN-XYZ")
    _install(monkeypatch, _runner(post=_FakeResp(503, {})))
    evs = await _collect(_turn())
    assert evs[0]["type"] == "error" and "503" in evs[0]["message"]
    assert "SECRET-TOKEN-XYZ" not in evs[0]["message"]


@pytest.mark.asyncio
async def test_a_poll_that_fails_reports_status_not_token(monkeypatch) -> None:
    _configure(monkeypatch, token="SECRET-TOKEN-XYZ")
    _install(monkeypatch, _runner(polls=[_FakeResp(502, {"detail": "credentials_exhausted"})]))
    evs = await _collect(_turn())
    assert evs == [{"type": "error", "message": "external engine returned 502"}]


@pytest.mark.asyncio
async def test_a_lost_ticket_is_named_as_a_restart(monkeypatch) -> None:
    """404 mid-poll is the runner's restart signal (robustness.md), never 'unknown'."""
    _configure(monkeypatch)
    _install(monkeypatch, _runner(polls=[_running(), _FakeResp(404, {})]))
    evs = await _collect(_turn())
    assert evs == [{"type": "error", "message": "external engine lost the turn (runner restarted)"}]


@pytest.mark.asyncio
async def test_a_running_poll_is_asked_again_until_done(monkeypatch) -> None:
    _configure(monkeypatch)
    seen: dict = {}
    _install(monkeypatch, _runner(polls=[_running(), _running(), _done({"text": "al fin"})], seen=seen))
    evs = await _collect(_turn())
    assert evs[0] == {"type": "text", "text": "al fin"}
    assert seen["polls"] == 3


@pytest.mark.asyncio
async def test_empty_answer_yields_error(monkeypatch) -> None:
    _configure(monkeypatch)
    _install(monkeypatch, _runner({"text": "   "}))
    assert await _collect(_turn()) == [{"type": "error", "message": "external engine returned an empty answer"}]


@pytest.mark.asyncio
async def test_a_reaction_only_turn_settles_with_its_reactions_not_as_an_error(monkeypatch) -> None:
    """server-bot F5: the engine returns the whole OutboundTurn. A turn that was
    only a `[REACT:]` used to arrive as text "" and became 'empty answer' here,
    although the persona had answered. The reaction is a gesture on the message,
    so it rides the result STRUCTURED (fi-glass renders chips) — never as text."""
    _configure(monkeypatch)
    _install(monkeypatch, _runner({"text": "", "reactions": ["👀", "🔥"], "empty_reason": "reactions_only", "model": "m"}))
    evs = await _collect(_turn(persona_id="insult"))
    assert evs == [{"type": "result", "result": {"text": "", "model": "m", "reactions": ["👀", "🔥"]}}]


@pytest.mark.asyncio
async def test_reactions_on_a_text_turn_ride_the_result_and_never_the_text(monkeypatch) -> None:
    _configure(monkeypatch)
    _install(monkeypatch, _runner({"text": "Vives en GDL.", "reactions": ["👀"], "model": "m"}))
    evs = await _collect(_turn(persona_id="insult"))
    assert evs == [
        {"type": "text", "text": "Vives en GDL."},
        {"type": "result", "result": {"text": "Vives en GDL.", "model": "m", "reactions": ["👀"]}},
    ]


def test_gifs_become_markdown_images_and_reactions_stay_out_of_the_body() -> None:
    data = {
        "text": "Ajá.",
        "reactions": ["👀"],
        "gif_urls": ["https://tenor.com/view/facepalm-1", "javascript:alert(1)"],
    }
    assert external_engine.render_outbound(data) == "Ajá.\n\n![gif](https://tenor.com/view/facepalm-1)"
    assert external_engine.outbound_reactions(data) == ["👀"]
    assert external_engine.render_outbound({"text": "solo texto"}) == "solo texto", "pre-F5 engines render as before"
    assert external_engine.outbound_reactions({"text": "solo texto"}) == []


@pytest.mark.asyncio
async def test_an_empty_turn_names_the_reason_the_engine_gave(monkeypatch) -> None:
    _configure(monkeypatch)
    _install(monkeypatch, _runner({"text": "", "empty_reason": "brain_empty"}))
    evs = await _collect(_turn(persona_id="insult"))
    assert evs == [{"type": "error", "message": "external engine returned an empty answer (brain_empty)"}]


@pytest.mark.asyncio
async def test_channel_id_is_the_conversation_id(monkeypatch) -> None:
    """OG118-CONTINUITY: the engine keys its long-lived session by channel_id
    (session_uuid is ignored by persona_runner). A hardcoded channel would pool
    EVERY user's conversations into one Claude session — the conversation id
    must be the channel."""
    _configure(monkeypatch)
    sent: dict = {}
    _install(monkeypatch, _runner(sent=sent))
    await _collect(_turn(session_uuid="conv-abc"))
    assert sent["channel_id"] == "conv-abc"
    assert sent["session_uuid"] == "conv-abc"


@pytest.mark.asyncio
async def test_no_session_falls_back_to_channel_zero(monkeypatch) -> None:
    _configure(monkeypatch)
    sent: dict = {}
    _install(monkeypatch, _runner(sent=sent))
    await _collect(_turn(session_uuid=None))
    assert sent["channel_id"] == "0"
    assert "session_uuid" not in sent


async def _payload(monkeypatch, **kwargs) -> dict:
    _configure(monkeypatch)
    sent: dict = {}
    _install(monkeypatch, _runner(sent=sent))
    await _collect(external_engine.stream_external_turn(persona_id="insult", user_text="hi", **kwargs))
    return sent


@pytest.mark.asyncio
async def test_a_person_in_a_conversation_asks_the_engine_to_run_the_pipeline(monkeypatch) -> None:
    """server-bot F3: og118 has no turn pipeline of its own, so the engine runs
    it — stores the turn, runs the guardian, grows the user's facts. `surface`
    lets the engine resolve the Auth0 sub to its canonical principal (F2)."""
    sent = await _payload(monkeypatch, session_uuid="conv-abc", user_id="google-oauth2|1")
    assert sent["pipeline"] == "runner"
    assert sent["surface"] == "og118"


@pytest.mark.asyncio
async def test_no_identity_or_no_conversation_never_runs_the_pipeline(monkeypatch) -> None:
    """A legacy-bearer caller (user_id None → "0") or a turn with no conversation
    id (channel "0") would pile strangers into one memory: bare turn only."""
    for kwargs in ({"session_uuid": "conv-abc", "user_id": None}, {"session_uuid": None, "user_id": "u"}):
        sent = await _payload(monkeypatch, **kwargs)
        assert "pipeline" not in sent, kwargs
        assert sent["surface"] == "og118"


@pytest.mark.asyncio
async def test_history_is_forwarded_capped(monkeypatch) -> None:
    """The replayed thread rides the payload (capped) so a fresh engine session —
    reaped slot, replica restart, element switched mid-conversation — can be
    seeded with the turns it never saw."""
    _configure(monkeypatch)
    sent: dict = {}
    _install(monkeypatch, _runner(sent=sent))
    history = [{"role": "user", "content": f"m{i}"} for i in range(30)]
    history.append({"role": "system", "content": "dropped: role not allowlisted"})
    await _collect(_turn(history=history))
    assert len(sent["history"]) == external_engine.HISTORY_MAX_MESSAGES - 1
    assert sent["history"][-1] == {"role": "user", "content": "m29"}
    assert all(m["role"] in {"user", "assistant"} for m in sent["history"])


def test_cap_history_char_budget_keeps_newest() -> None:
    big = "x" * external_engine.HISTORY_MAX_CHARS
    history = [
        {"role": "user", "content": big},
        {"role": "assistant", "content": "newest"},
    ]
    assert external_engine.cap_history(history) == [{"role": "assistant", "content": "newest"}]


def test_cap_history_empty_and_none() -> None:
    assert external_engine.cap_history(None) == []
    assert external_engine.cap_history([]) == []


@pytest.mark.asyncio
async def test_non_json_body_yields_error(monkeypatch) -> None:
    _configure(monkeypatch)
    _install(monkeypatch, _runner(polls=[_FakeResp(200, ValueError("not json"))]))
    assert await _collect(_turn()) == [{"type": "error", "message": "external engine returned a non-JSON body"}]


# --- the job id: the retry of a send is the SAME turn ---------------------------


def test_the_job_id_is_the_turn_not_the_attempt() -> None:
    history = [{"role": "user", "content": "antes"}]
    first = external_engine.turn_job_id("conv-abc", "hola", history)
    assert first == external_engine.turn_job_id("conv-abc", "hola", history), "a retry maps to the same ticket"
    assert first != external_engine.turn_job_id("conv-xyz", "hola", history), "another thread"
    assert first != external_engine.turn_job_id("conv-abc", "hola?", history), "another text"
    assert first != external_engine.turn_job_id("conv-abc", "hola", history * 2), "the same text later in the thread"
    assert first.isalnum() and len(first) == 32


def test_without_a_thread_every_send_is_its_own_job() -> None:
    assert external_engine.turn_job_id(None, "hola", None) != external_engine.turn_job_id(None, "hola", None)


@pytest.mark.asyncio
async def test_the_payload_carries_the_job_id(monkeypatch) -> None:
    sent = await _payload(monkeypatch, session_uuid="conv-abc", user_id="u")
    assert sent["job_id"] == external_engine.turn_job_id("conv-abc", "hi", None)


# --- the live tail: the engine's verbs arrive before its answer -----------------


TOOL_A = {"type": "tool_call", "tool": {"name": "mcp__memory__recall", "id": "t1", "server": "memory", "is_error": None}}
TOOL_B = {"type": "tool_call", "tool": {"name": "WebSearch", "id": "t2", "server": None, "is_error": None}}


@pytest.mark.asyncio
async def test_tool_calls_stream_live_before_the_answer(monkeypatch) -> None:
    _configure(monkeypatch)
    seen: dict = {}
    _install(
        monkeypatch,
        _runner(
            {"text": "listo", "model": "m"},
            events=[*_sse(1, TOOL_A), *_sse(2, TOOL_B), *DONE_LINES],
            poll_delay_s=0.1,
            seen=seen,
        ),
    )
    evs = await _collect(_turn())
    assert evs == [TOOL_A, TOOL_B, {"type": "text", "text": "listo"}, {"type": "result", "result": {"text": "listo", "model": "m"}}]
    assert seen["event_headers"][0]["Last-Event-ID"] == "0"
    assert "SECRET-TOKEN-XYZ" in seen["event_headers"][0]["Authorization"], "the tail is authenticated like the poll"


@pytest.mark.asyncio
async def test_an_events_stream_the_runner_refuses_does_not_break_the_turn(monkeypatch) -> None:
    """An older runner without the events door: no verbs, but the answer still lands."""
    _configure(monkeypatch)
    _install(monkeypatch, _runner({"text": "sin verbos"}, events_status=404, poll_delay_s=0.05))
    evs = await _collect(_turn())
    assert evs[0] == {"type": "text", "text": "sin verbos"}


@pytest.mark.asyncio
async def test_live_text_streams_and_the_final_text_is_not_appended_twice(monkeypatch) -> None:
    """OG118-EXTERNAL-TURN-2: the engine's text arrives as deltas on the event log.
    The reducer APPENDS `text` events and REPLACES on `result`, so once deltas
    streamed, the whole-text event must stay out — only `result` settles."""
    _configure(monkeypatch)
    _install(
        monkeypatch,
        _runner(
            {"text": "Chale, qué coraje.", "model": "m", "reactions": ["🔥"]},
            events=[*_sse(1, TOOL_B), *_sse(2, {"type": "text", "text": "Chale, "}), *_sse(3, {"type": "text", "text": "qué coraje."}), *DONE_LINES],
            poll_delay_s=0.1,
        ),
    )
    evs = await _collect(_turn())
    assert evs == [
        TOOL_B,
        {"type": "text", "text": "Chale, "},
        {"type": "text", "text": "qué coraje."},
        {"type": "result", "result": {"text": "Chale, qué coraje.", "model": "m", "reactions": ["🔥"]}},
    ]


@pytest.mark.asyncio
async def test_without_live_text_the_whole_text_still_arrives_once(monkeypatch) -> None:
    """An engine that streams no text (older runner, a reaction-only turn) keeps
    the `text` + `result` pair exactly as before."""
    _configure(monkeypatch)
    _install(monkeypatch, _runner({"text": "entero"}, events=[*_sse(1, TOOL_A), *DONE_LINES], poll_delay_s=0.05))
    evs = await _collect(_turn())
    assert evs == [TOOL_A, {"type": "text", "text": "entero"}, {"type": "result", "result": {"text": "entero", "model": None}}]


@pytest.mark.asyncio
async def test_frames_outside_the_live_set_are_not_forwarded(monkeypatch) -> None:
    _configure(monkeypatch)
    _install(
        monkeypatch,
        _runner({"text": "ok"}, events=[*_sse(1, {"type": "ping"}), *_sse(2, {"type": "result", "result": {"text": "no"}}), *DONE_LINES], poll_delay_s=0.05),
    )
    evs = await _collect(_turn())
    assert [e["type"] for e in evs] == ["text", "result"]
    assert evs[0]["text"] == "ok"


# --- the live wait and the deferred release --------------------------------------


LOST_TURN_2026_10_15_S = 125
ACA_INGRESS_REQUEST_TIMEOUT_S = 240


def test_live_wait_covers_the_engine_ceiling_plus_its_cold_start_and_no_request_nears_the_ingress_cap() -> None:
    live = external_engine.LIVE_WAIT_S
    assert live == external_engine.ENGINE_TURN_CEILING_S + external_engine.ENGINE_COLD_START_S
    assert live > LOST_TURN_2026_10_15_S
    assert live < ACA_INGRESS_REQUEST_TIMEOUT_S
    assert external_engine.POLL_WAIT_S <= 50.0, "persona_core.tickets.MAX_WAIT_S"
    assert external_engine._TIMEOUT.read < ACA_INGRESS_REQUEST_TIMEOUT_S
    assert external_engine._EVENTS_TIMEOUT.read < ACA_INGRESS_REQUEST_TIMEOUT_S


@pytest.mark.asyncio
async def test_a_late_answer_lands_in_the_thread_instead_of_being_dropped(monkeypatch) -> None:
    """The 2026-10-15 loss: the engine finished at 125s, og118 had cut at 95s."""
    _configure(monkeypatch)
    seen: dict = {}
    _install(monkeypatch, _runner({"text": "llegué tarde", "reactions": ["🔥"]}, poll_delay_s=0.2, seen=seen))
    delivered: list[dict] = []

    async def deliver(message: dict) -> None:
        delivered.append(message)

    evs = await _collect(_turn(live_wait_s=0.05, deliver_late=deliver))
    assert evs == [{"type": "deferred"}]
    await asyncio.sleep(0.4)
    assert len(delivered) == 1
    assert delivered[0]["role"] == "assistant"
    assert delivered[0]["content"] == "llegué tarde"
    assert delivered[0]["reactions"] == ["🔥"]
    assert delivered[0]["timestamp"].endswith("Z")
    assert seen["closed"] is True


@pytest.mark.asyncio
async def test_a_late_failure_is_delivered_as_a_visible_note(monkeypatch) -> None:
    _configure(monkeypatch)
    _install(monkeypatch, _runner(polls=[_FakeResp(502, {})], poll_delay_s=0.2))
    delivered: list[dict] = []

    async def deliver(message: dict) -> None:
        delivered.append(message)

    assert await _collect(_turn(live_wait_s=0.05, deliver_late=deliver)) == [{"type": "deferred"}]
    await asyncio.sleep(0.4)
    assert delivered[0]["role"] == "assistant"
    assert "502" in delivered[0]["content"]
    assert "Vuelve a mandar" in delivered[0]["content"]
    assert "SECRET-TOKEN" not in delivered[0]["content"]


@pytest.mark.asyncio
async def test_without_a_thread_to_deliver_to_the_cut_is_an_error(monkeypatch) -> None:
    _configure(monkeypatch)
    seen: dict = {}
    _install(monkeypatch, _runner({"text": "x"}, poll_delay_s=0.5, seen=seen))
    evs = await _collect(_turn(live_wait_s=0.05, deliver_late=None))
    assert len(evs) == 1 and evs[0]["type"] == "error"
    assert evs[0]["message"].startswith("external engine took longer than")
    assert seen["closed"] is True


def _persona_engine(monkeypatch, handler):
    monkeypatch.setattr(external_engine, "RUNNER_URL", "https://engine.test")
    monkeypatch.setattr(external_engine, "RUNNER_TOKEN", "tok")
    real = httpx.AsyncClient
    monkeypatch.setattr(
        external_engine.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)
    )


@pytest.mark.asyncio
async def test_put_persona_writes_with_the_engine_bearer(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"persona_id": "radon", "version": 3, "provider": "claude", "model": None})

    _persona_engine(monkeypatch, handler)
    out = await external_engine.put_persona("radon", {"display_name": "Radón", "dna": "x"})
    assert out["version"] == 3
    assert seen == {"url": "https://engine.test/v1/personas/radon", "auth": "Bearer tok",
                    "body": {"display_name": "Radón", "dna": "x"}}


@pytest.mark.asyncio
async def test_put_persona_surfaces_the_engine_refusal(monkeypatch):
    _persona_engine(monkeypatch, lambda r: httpx.Response(422, json={"detail": "belongs to the image"}))
    with pytest.raises(external_engine.PersonaWriteError) as e:
        await external_engine.put_persona("insult", {"display_name": "x", "dna": "x"})
    assert e.value.status == 422 and "belongs to the image" in str(e.value)


@pytest.mark.asyncio
async def test_put_persona_refuses_without_an_engine(monkeypatch):
    monkeypatch.setattr(external_engine, "RUNNER_URL", "")
    with pytest.raises(external_engine.PersonaWriteError) as e:
        await external_engine.put_persona("radon", {})
    assert e.value.status == 503
