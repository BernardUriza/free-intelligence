"""The server IS the interface — and it is a SUBSTITUTE for the Claude API.

Your apps stop calling `api.anthropic.com` and call AIRE. Same slot (an HTTP
endpoint, not a library you import), but AIRE remembers (Postgres) and lets
itself be watched (SSR). A single route serves both audiences, because it is
the SAME turn and the SAME event stream:

    Accept: text/html          → the page that writes itself   (you, watching)
    Accept: text/event-stream  → the raw events                (your apps)

And `?mode=` picks the dial: `complete` (bare substitute) or `agent` (enhancer
that executes tools).

AUTHENTICATION — the LLM door (``AIRE_AUTH_TOKEN``). Every turn burns real
Anthropic tokens, so every route except ``/health`` is gated by a long secret
only Bernard holds. Two ways in, one per audience:

- an app sends ``Authorization: Bearer <token>`` (the cookbook's pattern);
- a browser opens any URL once with ``?token=<token>`` — the server sets an
  ``aire_token`` cookie and redirects to the clean URL, so the page (and the
  ``<form>`` POSTs it makes) keep working without the secret in every link.

Unset token = fail CLOSED (503): a forgotten env var must never mean an open
LLM. Comparison is constant-time.
"""

from __future__ import annotations

import hmac
import json
import os
from collections.abc import AsyncIterator
from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

from . import render
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
    return request.query_params.get("token") or request.cookies.get("aire_token") or ""


@app.middleware("http")
async def llm_door(request: Request, call_next: Any) -> Any:
    if request.url.path == "/health":
        return await call_next(request)
    if not AUTH_TOKEN:
        return JSONResponse({"detail": "AIRE_AUTH_TOKEN is not configured"}, status_code=503)
    if not hmac.compare_digest(_presented_token(request), AUTH_TOKEN):
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    if request.query_params.get("token"):
        clean_q = "&".join(f"{k}={v}" for k, v in request.query_params.items() if k != "token")
        response = RedirectResponse(
            request.url.path + (f"?{clean_q}" if clean_q else ""), status_code=303
        )
        response.set_cookie(
            "aire_token", AUTH_TOKEN, httponly=True, secure=False, samesite="lax",
            max_age=60 * 60 * 24 * 30,
        )
        return response
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


@app.get("/")
async def index() -> RedirectResponse:
    return RedirectResponse("/projects/aire/sessions/hello")


@app.get("/projects/{project}/sessions/{session}", response_class=HTMLResponse)
async def session_page(project: str, session: str, mode: str | None = None) -> HTMLResponse:
    project, session = safe_names(project, session)
    mode = safe_mode(mode)
    engine = await get_engine()
    entries = await engine.load_transcript(project, session)
    return HTMLResponse(render.landing(project, session, mode, entries))


@app.post("/projects/{project}/sessions/{session}/messages")
async def post_message(project: str, session: str, request: Request) -> Any:
    project, session = safe_names(project, session)
    message, mode = await _read_body(request)
    mode = safe_mode(mode)
    # An empty message is NOT a turn: sending it to the SDK is a real query that
    # spends money for nothing. The edge cuts it before it touches the agent.
    if not message:
        return RedirectResponse(f"/projects/{project}/sessions/{session}?mode={mode}", status_code=303)
    if "text/event-stream" in request.headers.get("accept", ""):
        return EventSourceResponse(_events(project, session, message, mode))
    return StreamingResponse(
        _html(project, session, message, mode),
        media_type="text/html; charset=utf-8",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
    )


async def _read_body(request: Request) -> tuple[str, str | None]:
    """A `<form>` posts urlencoded; an app posts JSON. Both get in."""
    if request.headers.get("content-type", "").startswith("application/json"):
        body = await request.json()
        return str(body.get("message", body.get("prompt", ""))).strip(), body.get("mode")
    form = await request.form()
    return str(form.get("message", "")).strip(), form.get("mode")  # type: ignore[return-value]


async def _html(project: str, session: str, message: str, mode: str) -> AsyncIterator[bytes]:
    yield render.head(project, session, mode, message)
    engine = await get_engine()
    async for ev in engine.run_stream(project, session, message, mode):
        chunk = render.event(ev)
        if chunk:
            yield chunk
    yield render.foot(project, session, mode)


async def _events(project: str, session: str, message: str, mode: str) -> AsyncIterator[ServerSentEvent]:
    engine = await get_engine()
    async for ev in engine.run_stream(project, session, message, mode):
        yield ServerSentEvent(event=ev["type"], data=json.dumps(_plain(ev), ensure_ascii=False))
    yield ServerSentEvent(event="done", data=json.dumps({"session": session, "mode": mode}))


def _plain(ev: dict[str, Any]) -> dict[str, Any]:
    return {k: asdict(v) if is_dataclass(v) and not isinstance(v, type) else v for k, v in ev.items()}
