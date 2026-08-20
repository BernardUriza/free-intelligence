"""The message surface — POST a turn and GET a session's background status.

`POST …/messages` runs one turn: an SSE event stream by default, or fire-and-
forget when the body carries `background: true` (#22a) — the turn survives a
dropped socket; its result is read back via the artifacts endpoint (#22b) or the
mirrored transcript. Events, never HTML ([[write-only-daemon]])."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

from . import tokens
from .deps import get_engine
from .engine import DEFAULT_MODE, MODES, BudgetExceeded, SlotBusy, TurnSpec
from .engine.drain import turn_cost
from .engine.tools import UnknownTool, clean_tools
from .engine.vision import BadImage, clean_images
from .names import InvalidName, clean

router = APIRouter()

MODEL_SHAPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def safe_names(project: str, session: str) -> tuple[str, str]:
    try:
        return clean("project", project), clean("session", session)
    except InvalidName as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def safe_mode(mode: str | None) -> str:
    return mode if mode in MODES else DEFAULT_MODE


@router.post("/projects/{project}/sessions/{session}/messages")
async def post_message(project: str, session: str, request: Request) -> Any:
    project, session = safe_names(project, session)
    body = await request.json()
    message = str(body.get("message", body.get("prompt", ""))).strip()
    mode = safe_mode(body.get("mode"))
    spec = TurnSpec(mode=mode, tools=safe_tools(body.get("tools"), mode),
                    model=safe_model(body.get("model")))
    images = safe_images(body.get("images"))
    # An empty turn spends real money for nothing, so the edge cuts it. An
    # image-only send IS a turn (#29 gap 4): the picture is the message.
    if not message and not images:
        raise HTTPException(status_code=422, detail="empty message")
    holder = getattr(request.state, "holder", None)  # an invited key (#32d), or Bernard's
    if bool(body.get("background")):  # #22a — fire-and-forget, survives a dropped socket
        return await _launch_background(project, session, message, spec, images, holder)
    return EventSourceResponse(_events(project, session, message, spec, images, holder))


def safe_tools(raw: Any, mode: str) -> tuple[str, ...]:
    """Validate the `tools` field against the vetted registry (#29). A tool turn
    needs the agentic loop, so tools with mode=complete is a 422, not a silent
    prompt-and-hang."""
    try:
        names = clean_tools(raw)
    except UnknownTool as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if names and mode == "complete":
        raise HTTPException(status_code=422, detail="tools require mode=agent")
    return tuple(names)


def safe_model(raw: Any) -> str | None:
    """The `model` field (#29 gap 3) rides verbatim to the CLI as `--model`; the
    edge guards only the argv's shape — the API curates the catalog. Absent →
    the engine decides. Binds when the session's pooled client is (re)born."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, str) and MODEL_SHAPE.match(raw):
        return raw
    raise HTTPException(status_code=422, detail="invalid model")


def safe_images(raw: Any) -> tuple[dict[str, str], ...]:
    """Attachments for THIS turn (#29 gap 4), validated in `engine/vision.py`."""
    try:
        return clean_images(raw)
    except BadImage as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


async def _bank(holder: Any, cost: float) -> None:
    """Charge one turn to the invited key that asked for it (#32d/#28). A real
    result that bills nothing is PRINTED, never swallowed: that is precisely what
    a ceiling looks like while it is not biting, and it stayed invisible once."""
    if cost <= 0:
        print(f"INVITE {holder.nickname}: a turn banked $0 — the ceiling is not biting", flush=True)
    await tokens.charge(holder.nickname, cost)


async def _launch_background(project: str, session: str, message: str, spec: TurnSpec,
                             images: tuple[dict[str, str], ...],
                             holder: Any = None) -> JSONResponse:
    engine = await get_engine()
    sink = (lambda cost: _bank(holder, cost)) if holder is not None else None
    try:
        engine.launch_detached(project, session, message, spec, images, on_cost=sink)
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


async def _events(project: str, session: str, message: str, spec: TurnSpec,
                  images: tuple[dict[str, str], ...],
                  holder: Any = None) -> AsyncIterator[ServerSentEvent]:
    engine = await get_engine()
    try:
        async for ev in engine.run_stream(project, session, message, spec, images):
            # An invited key pays for its own turn (#32d/#28). Banked as the result
            # passes, not at the end: a dropped socket must not make a turn free.
            if holder is not None and ev.get("type") == "result":
                await _bank(holder, turn_cost(ev))
            yield ServerSentEvent(event=ev["type"], data=json.dumps(_plain(ev), ensure_ascii=False))
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


def _plain(ev: dict[str, Any]) -> dict[str, Any]:
    return {k: asdict(v) if is_dataclass(v) and not isinstance(v, type) else v for k, v in ev.items()}
