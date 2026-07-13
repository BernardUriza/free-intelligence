"""El servidor ES la interfaz — y es un SUSTITUTO de la Claude API.

Tus apps dejan de llamar a `api.anthropic.com` y llaman a AIRE. Mismo slot (un
endpoint HTTP, no una librería que importas), pero AIRE se acuerda (Postgres) y se
deja mirar (SSR). Una sola ruta atiende a los dos públicos, porque es el MISMO
turno y el MISMO stream de eventos:

    Accept: text/html          → la página que se escribe sola   (tú, mirando)
    Accept: text/event-stream  → los eventos crudos              (tus apps)

Y el `?mode=` elige el dial: `complete` (sustituto pelón) o `agent` (mejorador que
ejecuta tools).

SIN AUTENTICACIÓN todavía — a propósito, y dicho de frente: esto es local. El
patrón Bearer del server oficial se enchufa después; mientras no esté, no se
expone fuera de localhost.
"""

from __future__ import annotations

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

app = FastAPI(title="AIRE", description="Sustituto y mejorador de la Claude API")

_engine: Engine | None = None


async def get_engine() -> Engine:
    global _engine
    if _engine is None:
        store = await create_postgres_session_store(DSN)
        _engine = Engine(store)
    return _engine


def _drop_engine() -> None:
    """El pool cacheado (store + clientes) muere con la base; que el próximo
    request lo reconstruya contra la base ya viva."""
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
    """Estado REAL de la memoria, incluida la base caída, sin reventar. Un health
    que responde 500 con traceback no sirve para monitorear."""
    try:
        engine = await get_engine()
        await engine.session_store.list_sessions("__health__")
        return JSONResponse({"status": "ok", "memoria": "postgres", "modos": list(MODES)})
    except Exception as exc:  # noqa: BLE001 — el health captura TODO, ése es su trabajo
        _drop_engine()
        return JSONResponse(
            {"status": "degraded", "memoria": "unreachable", "detail": type(exc).__name__},
            status_code=503,
        )


@app.get("/")
async def index() -> RedirectResponse:
    return RedirectResponse("/projects/aire/sessions/hola")


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
    # Un mensaje vacío NO es un turno: mandarlo al SDK es un query real que gasta
    # dinero por nada. El borde lo corta antes de tocar al agente.
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
    """Un `<form>` postea urlencoded; una app postea JSON. Los dos entran."""
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
