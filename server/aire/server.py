"""AIRE's HTTP surface — events and files, NEVER a view.

Your apps stop calling `api.anthropic.com` and call AIRE. Same slot (an HTTP
endpoint, not a library you import), but AIRE remembers (Postgres). This
server emits **no HTML, ever** — Bernard's law, twice over:

- [[write-only-daemon]]: every reader/view is a waiter and every waiter lives
  in the front repo (`aire-front`). This repo holds the pen, not the menu.
- The daemon's mouths are `/health` (JSON), the message router (SSE events +
  the #22a background launch), and the artifacts router (#22b — RAW file bytes,
  never HTML, reaching the droplet's DISK not the database). Rendering events
  into pixels is the front's job.

This module is only the wiring: the app, the auth middleware, `/health`, and the
routers. The endpoints live in `messages.py` and `artifacts.py` (one surface per
module — the thirty-line file law); the engine singleton lives in `deps.py`.

AUTHENTICATION — the LLM door (``AIRE_AUTH_TOKEN``). Every turn burns real
Anthropic tokens, so everything except ``/health`` is gated by a long secret
only Bernard holds: ``Authorization: Bearer <token>``. Unset token = fail
CLOSED (503): a forgotten env var must never mean an open LLM. Comparison is
constant-time.
"""

from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import artifacts, messages
from .deps import drop_engine, get_engine
from .engine import MODES

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
        drop_engine()
        return JSONResponse(
            {"status": "degraded", "memory": "unreachable", "detail": type(exc).__name__},
            status_code=503,
        )


app.include_router(messages.router)   # POST a turn (SSE or #22a background), GET status
app.include_router(artifacts.router)  # GET the casita's files — #22b, the daemon's disk surface
