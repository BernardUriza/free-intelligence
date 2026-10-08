"""The message surface — POST a turn and GET a session's background status.

`POST …/messages` runs one turn: an SSE stream, or fire-and-forget with
`background: true` (#22a) — it survives a dropped socket; its result is read back
via the artifacts endpoint (#22b) or the transcript. Events, never HTML."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

from . import tokens
from .deps import get_engine
from .engine import BudgetExceeded, SlotBusy, TurnSpec
from .engine.contract import Guard
from .engine.drain import turn_cost
from .engine.guards import observe
from .engine.vision import attached_counts
from .attachment_door import safe_attachments
from .intake import build_guards, safe_guard_names, safe_names, safe_provider, turn_spec

router = APIRouter()


@router.post("/projects/{project}/sessions/{session}/messages")
async def post_message(project: str, session: str, request: Request) -> Any:
    project, session = safe_names(project, session)
    body = await request.json()
    message = str(body.get("message", body.get("prompt", ""))).strip()
    spec = turn_spec(body, getattr(request.state, "lane", ""))  # the door named the lane
    engine = await get_engine()
    attachments = await safe_attachments(body.get("images"), body.get("documents"),
                                         engine.session_key(project, session), spec.provider)
    guard_names = safe_guard_names(body.get("guards"))
    # An empty turn spends real money for nothing, so the edge cuts it. An
    # attachment-only send IS a turn (#29 gap 4): the picture is the message.
    if not message and not attachments:
        raise HTTPException(status_code=422, detail="empty message")
    holder = getattr(request.state, "holder", None)  # an invited key (#32d), or Bernard's
    if bool(body.get("background")):  # #22a — fire-and-forget, survives a dropped socket
        if guard_names:
            # A guard's whole output is a stream event. A detached turn has no
            # stream, so honouring `guards` here would build them and discard
            # their findings — a request accepted and silently ignored. Checked
            # BEFORE building: the shape of the request is the caller's problem
            # and answers the same on every box; a missing backing is neither.
            raise HTTPException(status_code=422, detail="guards need a stream; drop `background`")
        return await _launch_background(project, session, message, spec, attachments, holder)
    guards = build_guards(guard_names)
    return EventSourceResponse(_events(project, session, message, spec, attachments, holder, guards))


async def _bank(holder: Any, cost: float) -> None:
    """Charge one turn to the invited key that asked for it (#32d/#28). A real
    result that bills nothing is PRINTED, never swallowed: that is precisely what
    a ceiling looks like while it is not biting, and it stayed invisible once."""
    if cost <= 0:
        print(f"INVITE {holder.nickname}: a turn banked $0 — the ceiling is not biting", flush=True)
    await tokens.charge(holder.nickname, cost)


async def _launch_background(project: str, session: str, message: str, spec: TurnSpec,
                             attachments: tuple[dict[str, Any], ...],
                             holder: Any = None) -> JSONResponse:
    engine = await get_engine()
    sink = (lambda cost: _bank(holder, cost)) if holder is not None else None
    try:
        engine.launch_detached(project, session, message, spec, attachments, on_cost=sink)
    except RuntimeError as exc:  # a turn already runs on this session
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return JSONResponse({"status": "accepted", "session": session}, status_code=202)


@router.get("/projects/{project}/sessions/{session}/status")
async def session_status(project: str, session: str) -> JSONResponse:
    """Is a background turn (#22a) still running on this session?"""
    project, session = safe_names(project, session)
    engine = await get_engine()
    return JSONResponse({"session": session,
                         "running": engine.detached.running(f"{project}/{session}")})


@router.get("/projects/{project}/sessions/{session}")
async def session_exists(project: str, session: str, provider: str | None = None) -> JSONResponse:
    """Does this session already hold a transcript AIRE can resume?

    A caller that keeps its own conversation history needs this before a turn:
    replaying that history into a session that ALREADY holds it pays for the
    same tokens twice and buries the tool_use/tool_result blocks a text replay
    cannot carry. The read is the engine's own `has_session` — the SDK's resume
    check ([[write-only-daemon]] exception 1): it feeds the machine's decision
    about how to send the turn, never a human's eyes.
    """
    project, session = safe_names(project, session)
    engine = await get_engine()
    return JSONResponse({"session": session,
                         "exists": await engine.has_session(project, session, safe_provider(provider))})


async def _events(project: str, session: str, message: str, spec: TurnSpec,
                  attachments: tuple[dict[str, Any], ...],
                  holder: Any = None,
                  guards: list[Guard] | None = None) -> AsyncIterator[ServerSentEvent]:
    engine = await get_engine()
    try:
        async for ev in engine.run_stream(project, session, message, spec, attachments):
            if ev.get("type") == "result":  # #50: the consumer checks this against what it sent
                ev = {**ev, **attached_counts(attachments)}
            # An invited key pays for its own turn (#32d/#28). Banked as the result
            # passes, not at the end: a dropped socket must not make a turn free.
            if holder is not None and ev.get("type") == "result":
                await _bank(holder, turn_cost(ev))
            yield ServerSentEvent(event=ev["type"], data=json.dumps(_plain(ev), ensure_ascii=False))
            if guards and ev.get("type") == "result":
                yield _guards_event(guards, ev, message)
    except BudgetExceeded as exc:
        # The spend ceiling was hit BEFORE the turn touched the API. Tell the
        # caller in-stream (the connection is already an event stream, so a 402
        # header is no longer possible) instead of a silent stall.
        yield ServerSentEvent(event="error", data=json.dumps({"error": "budget_exceeded", "detail": str(exc)}))
    except SlotBusy as exc:
        # The box was full and the queue wait timed out (backpressure). The stream
        # is already 200, so say retry in-stream rather than a 503 header.
        yield ServerSentEvent(event="error", data=json.dumps({"error": "slot_busy", "detail": str(exc)}))
    yield ServerSentEvent(event="done", data=json.dumps({"session": session, "mode": spec.mode}))


def _guards_event(guards: list[Guard], result_ev: dict[str, Any], message: str) -> ServerSentEvent:
    """What the guards saw, after the text the caller already read. Observational
    by construction — see `guards.run.observe`. A guard that raises is reported,
    never fatal: the turn already succeeded and its answer is already delivered."""
    text = getattr(result_ev.get("result"), "text", "") or ""
    return ServerSentEvent(event="guards",
                           data=json.dumps(_plain(observe(guards, text, message)), ensure_ascii=False))


def _plain(ev: dict[str, Any]) -> dict[str, Any]:
    return {k: asdict(v) if is_dataclass(v) and not isinstance(v, type) else v for k, v in ev.items()}
