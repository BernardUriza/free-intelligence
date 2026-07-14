"""AIRE's HTTP surface — events only, NEVER a view.

Your apps stop calling `api.anthropic.com` and call AIRE. Same slot (an HTTP
endpoint, not a library you import), but AIRE remembers (Postgres). This
server emits **no HTML, ever** — Bernard's law, twice over:

- [[write-only-daemon]]: every reader/view is a waiter and every waiter lives
  in the front repo (`aire-front`). This repo holds the pen, not the menu.
- The daemon's only mouths are `/health` (JSON) and the message endpoint
  (SSE events). Rendering those events into pixels is the front's job.

`?mode=` picks the dial: `complete` (bare substitute for the raw API) or
`agent` (enhancer that executes tools inside the session's casita).

AUTHENTICATION — the LLM door (``AIRE_AUTH_TOKEN``). Every turn burns real
Anthropic tokens, so everything except ``/health`` is gated by a long secret
only Bernard holds: ``Authorization: Bearer <token>``. Unset token = fail
CLOSED (503): a forgotten env var must never mean an open LLM. Comparison is
constant-time.
"""

from __future__ import annotations

import hmac
import json
import os
from collections.abc import AsyncIterator
from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

from .engine import DEFAULT_MODE, MODES, Engine
from .names import InvalidName, clean
from .store import create_postgres_session_store

DSN = os.environ.get("AIRE_DSN", "postgresql://bernardurizaorozco@127.0.0.1:5432/aire")
AUTH_TOKEN = os.environ.get("AIRE_AUTH_TOKEN", "")

app = FastAPI(title="AIRE", description="Substitute for and enhancer of the Claude API")


def _presented_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return ""


@app.middleware("http")
async def llm_door(request: Request, call_next: Any) -> Any:
    if request.url.path == "/health":
        return await call_next(request)
    if not AUTH_TOKEN:
        return JSONResponse({"detail": "AIRE_AUTH_TOKEN is not configured"}, status_code=503)
    if not hmac.compare_digest(_presented_token(request), AUTH_TOKEN):
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    return await call_next(request)


_engine: Engine | None = None


async def get_engine() -> Engine:
    global _engine
    if _engine is None:
        store = await create_postgres_session_store(DSN)
        _engine = Engine(store)
    return _engine


def _drop_engine() -> None:
    """The cached pool (store + clients) dies with the database; let the next
    request rebuild it against the database once it's back up."""
    global _engine
    _engine = None


def safe_names(project: str, session: str) -> tuple[str, str]:
    try:
        return clean("project", project), clean("session", session)
    except InvalidName as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def safe_mode(mode: str | None) -> str:
    return mode if mode in MODES else DEFAULT_MODE


@app.get("/health")
async def health() -> JSONResponse:
    """The REAL state of the memory, including a downed database, without
    blowing up. A health endpoint that answers 500 with a traceback is useless
    for monitoring."""
    try:
        engine = await get_engine()
        await engine.session_store.list_sessions("__health__")
        return JSONResponse({"status": "ok", "memory": "postgres", "modes": list(MODES)})
    except Exception as exc:  # noqa: BLE001 — health catches EVERYTHING, that's its job
        _drop_engine()
        return JSONResponse(
            {"status": "degraded", "memory": "unreachable", "detail": type(exc).__name__},
            status_code=503,
        )


@app.post("/projects/{project}/sessions/{session}/messages")
async def post_message(project: str, session: str, request: Request) -> Any:
    project, session = safe_names(project, session)
    body = await request.json()
    message = str(body.get("message", body.get("prompt", ""))).strip()
    mode = safe_mode(body.get("mode"))
    # An empty message is NOT a turn: sending it to the SDK is a real query that
    # spends money for nothing. The edge cuts it before it touches the agent.
    if not message:
        raise HTTPException(status_code=422, detail="empty message")
    return EventSourceResponse(_events(project, session, message, mode))


async def _events(project: str, session: str, message: str, mode: str) -> AsyncIterator[ServerSentEvent]:
    engine = await get_engine()
    async for ev in engine.run_stream(project, session, message, mode):
        yield ServerSentEvent(event=ev["type"], data=json.dumps(_plain(ev), ensure_ascii=False))
    yield ServerSentEvent(event="done", data=json.dumps({"session": session, "mode": mode}))


def _plain(ev: dict[str, Any]) -> dict[str, Any]:
    return {k: asdict(v) if is_dataclass(v) and not isinstance(v, type) else v for k, v in ev.items()}
