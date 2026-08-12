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

AUTHENTICATION — the LLM door. Every turn burns real Anthropic tokens, so
everything except ``/health`` is gated by a long Bearer secret. Two tokens are
accepted: ``AIRE_AUTH_TOKEN`` (Bernard's own) and an optional
``AIRE_CANARY_TOKEN`` — a second, independently revocable key handed to a
lower-trust consumer (the Azure front). A leak of the canary is revoked by
dropping that one env var and restarting; Bernard's own key never rotates for
it. Both fail CLOSED (503) when neither is set: a forgotten env var must never
mean an open LLM. Comparison is constant-time.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import access, artifacts, gateway, init_project, messages, tokens
from .bearer import ACCEPTED_TOKENS, accepted, presented_token
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


@app.middleware("http")
async def llm_door(request: Request, call_next: Any) -> Any:
    if request.url.path == "/health":
        return await call_next(request)
    # The gateway door (#30) is auth-PASS-THROUGH, not auth-free: the caller's
    # own Anthropic credential rides upstream and upstream judges it. AIRE
    # spends nothing of its own there. Per-consumer AIRE tokens are backlog #28.
    if request.url.path.startswith("/v1/"):
        return await call_next(request)
    # The approve/revoke links (#32) are clicked from a mail client, which cannot
    # carry a Bearer token. Their HMAC signature IS their authentication, and the
    # verb is signed INTO it so one cannot be replayed as the other — access.py.
    if request.url.path in ("/access/approve", "/access/revoke"):
        return await call_next(request)
    if not ACCEPTED_TOKENS:
        return JSONResponse({"detail": "no LLM-door token is configured"}, status_code=503)
    presented = presented_token(request)
    if accepted(presented):
        return await call_next(request)
    refusal = _admit_invited(request, presented)
    return refusal if refusal else await call_next(request)


def _admit_invited(request: Request, presented: str) -> JSONResponse | None:
    """An invited stranger's own key (#32d). It carries a ceiling of its own, so a
    leaked invitation cannot burn the global budget (#28) — and an empty one is a
    402, not a 401: the key is real, its money is gone. `None` means admitted."""
    holder = tokens.identify(presented)
    if holder is None:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    if holder.exhausted():
        return JSONResponse(
            {"detail": f"{holder.nickname} has spent its budget", "error": "token_budget_spent"},
            status_code=402,
        )
    request.state.holder = holder
    return None


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
app.include_router(gateway.router)    # /v1/* — the gateway door (#30), Messages wire format
app.include_router(artifacts.router)  # GET the casita's files — #22b, the daemon's disk surface
app.include_router(init_project.router)  # POST init — set a casita's fixed prompt (CLAUDE.md)
app.include_router(access.router)     # #32 — a stranger asks to be let in; Bernard's inbox decides
