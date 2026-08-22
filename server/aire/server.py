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

Who is admitted, under whose ceiling, holding which slot, lives in `door.py` —
it left this module the day admission stopped being one Bearer comparison and
became per-key budgets, credential lending and a concurrency slot's lifetime.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from . import access, arming, artifacts, door, gateway, init_project, messages, tokens
from .deps import drop_engine, get_engine
from .engine import MODES


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """The invited keys (#32d), once. A database that is down must not make the
    door refuse Bernard's own token too — it degrades to the two constants."""
    try:
        await tokens.load()
    except Exception as exc:  # noqa: BLE001 — a blank roster survives; a dead door does not
        print(f"invite tokens unavailable at startup: {exc!r}", flush=True)
    yield


app = FastAPI(
    title="AIRE",
    description="Substitute for and enhancer of the Claude API",
    lifespan=lifespan,
)


app.add_middleware(BaseHTTPMiddleware, dispatch=door.llm_door)


@app.get("/health")
async def health() -> JSONResponse:
    """The REAL state of the memory, including a downed database, without
    blowing up. A health endpoint that answers 500 with a traceback is useless
    for monitoring.

    It also reports which GUARDS are armed (`arming.py`). Reachable memory was
    the only thing this ever proved, so a daemon whose spend backstop never
    armed, whose rotor had one slot and whose verbs all answered DENIED still
    read `{"status": "ok"}` — green for a box where every safety was off."""
    try:
        engine = await get_engine()
        await engine.session_store.list_sessions("__health__")
        return JSONResponse({"status": "ok", "memory": "postgres",
                             "modes": list(MODES), **arming.report()})
    except Exception as exc:  # noqa: BLE001 — health catches EVERYTHING, that's its job
        drop_engine()
        return JSONResponse(
            {"status": "degraded", "memory": "unreachable",
             "detail": type(exc).__name__, **arming.report()},
            status_code=503,
        )


app.include_router(messages.router)   # POST a turn (SSE or #22a background), GET status
app.include_router(gateway.router)    # /v1/* — the gateway door (#30), Messages wire format
app.include_router(artifacts.router)  # GET the casita's files — #22b, the daemon's disk surface
app.include_router(init_project.router)  # POST init — set a casita's fixed prompt (CLAUDE.md)
app.include_router(access.router)     # #32 — a stranger asks to be let in; Bernard's inbox decides
