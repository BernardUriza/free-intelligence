"""Who is admitted, under whose ceiling, holding which slot — the LLM door.

Every turn burns real Anthropic tokens, so everything except ``/health`` is
gated here. Three kinds of caller pass, and they are not variations of one
check — they are three contracts:

- **A constant token** (``bearer.ACCEPTED_TOKENS``): Bernard's own, the Azure
  front's canary, the persona-runner's. One slot per CONSUMER, revocable alone.
  They fail CLOSED (503) when none is set — a forgotten env var must never mean
  an open LLM.
- **An invited key** (#32d): minted per nickname, capped per nickname, so a
  leaked invitation cannot burn the global budget (#28). An empty one answers
  402, not 401 — the key is real, its money is gone.
- **Nobody at all**, on the gateway door: auth-pass-through. A caller carrying
  their own Anthropic credential is relayed and AIRE spends nothing on them.

This left ``server.py`` on 2026-08-22 because that module's own docstring calls
itself "only the wiring", and admission had quietly grown into four functions
holding per-key ceilings, credential lending and a concurrency slot's lifetime.
``bearer.py`` answers "is this token one of ours"; this module answers
everything that follows from the answer.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from . import lending, tokens
from .bearer import ACCEPTED_TOKENS, accepted, presented_token
from .engine.lanes import lane_of


async def llm_door(request: Request, call_next: Any) -> Any:
    if request.url.path == "/health":
        return await call_next(request)
    if request.url.path.startswith("/v1/"):
        return await gateway_door(request, call_next)
    # The approve/revoke links (#32) are clicked from a mail client, which cannot
    # carry a Bearer token. Their HMAC signature IS their authentication, and the
    # verb is signed INTO it so one cannot be replayed as the other — access.py.
    if request.url.path in ("/access/approve", "/access/revoke"):
        return await call_next(request)
    if not ACCEPTED_TOKENS:
        return JSONResponse({"detail": "no LLM-door token is configured"}, status_code=503)
    presented = presented_token(request)
    if accepted(presented):
        request.state.lane = lane_of(presented)  # a consumer with its own credential (lanes.py)
        return await call_next(request)
    refusal = _admit_invited(request, presented)
    return refusal if refusal else await call_next(request)


async def gateway_door(request: Request, call_next: Any) -> Any:
    """Admission to the gateway door, and the LIFETIME of the slot it claims.

    The slot is returned here only when no handler took it over — the relay
    outlives this frame and frees its own. What this catches is the request that
    reached no handler at all: a 404 on an undefined `/v1/` path claimed a slot
    that nobody ever gave back, so two typos locked an invited key out of the
    real door until the daemon restarted."""
    refusal = _admit_gateway(request)
    if refusal is not None:
        return refusal
    try:
        return await call_next(request)
    finally:
        lending.release(request.state)


def _admit_gateway(request: Request) -> JSONResponse | None:
    """The gateway door stays auth-PASS-THROUGH for anyone carrying their own
    Anthropic credential and no AIRE key — AIRE spends nothing on them and
    judges nothing. An AIRE key (as the Bearer, or in `x-aire-key` when the
    Bearer slot carries the caller's own OAuth) puts the turn under that key's
    ceiling: lent credential for an invited key (#32), metered pass-through
    beside the caller's own (#34). `None` means carry on."""
    holder = tokens.identify(request.headers.get("x-aire-key", "")
                             or presented_token(request))
    if holder is None:
        return None
    if holder.exhausted():
        return JSONResponse(
            {"type": "error", "error": {"type": "invalid_request_error",
             "message": f"AIRE: {holder.nickname} has spent its budget"}}, status_code=402)
    if not lending.claim(request.state, holder.nickname):
        return JSONResponse(
            {"type": "error", "error": {"type": "rate_limit_error",
             "message": f"AIRE: {holder.nickname} already has {lending.MAX_INFLIGHT} turns in flight"}},
            status_code=429)
    request.state.holder = holder
    return None


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
