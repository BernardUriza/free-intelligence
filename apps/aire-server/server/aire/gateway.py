"""The gateway door (#30): the Anthropic Messages wire format, proxied.

Claude Code (or anything speaking the Messages API) points ANTHROPIC_BASE_URL
at AIRE, Bedrock-style, and changes nothing else. Each request forwards to the
upstream verbatim — every ``anthropic-*`` header, the body, and the ``system``
array exactly as received (the attribution block must stay first or upstream
stops stripping it) — and the response relays byte-for-byte AS IT ARRIVES:
``ping`` events and SSE comment lines included, because the client counts every
byte and aborts a stream silent for 300 seconds. Upstream errors relay
unwrapped — Claude Code pattern-matches their wording to auto-retry. Both
halves are appended to ``aire_gateway_log`` on the side (``gateway_mirror``);
the mirror never fails the relay.

Auth is pass-through by default: the caller's own credential rides upstream,
AIRE adds none and stores none. An AIRE key changes that. An INVITED key (#32)
has no Anthropic credential by construction — AIRE lends its own (``lending``)
and bills against that key's ceiling, the one path where this door spends
AIRE's money. A METERED key (#34) rides beside the caller's own credential
(``x-aire-key``, or the Bearer next to an ``x-api-key``): nothing is lent,
their credential relays, and the same prices bank against the same ceiling —
a cap that counts and cuts off a client AIRE spends nothing on.

This router sits BELOW the engine and never imports from ``engine/`` — serving
it through the SDK would recurse (the spawned CLI calling the daemon back).
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from . import gateway_mirror, lending, tokens
from .bearer import presented_token
from .gateway_mirror import ResponseTap
from .relay import forward

router = APIRouter()

# Hop-by-hop and transport headers are the proxy's own business; everything
# else — anthropic-version, anthropic-beta (never allowlisted), x-claude-code-*
# — forwards verbatim. x-aire-project and x-aire-key are addressed to AIRE,
# consumed here. accept-encoding is forced to identity so the relayed bytes are
# the SSE text itself (the mirror tap must read them), never a gzip frame.
_SKIP_REQUEST = {"host", "content-length", "connection", "keep-alive", "te",
                 "trailer", "transfer-encoding", "upgrade", "proxy-authenticate",
                 "proxy-authorization", "accept-encoding", "x-aire-project",
                 "x-aire-key"}



def _upstream() -> str:
    return os.environ.get("AIRE_GATEWAY_UPSTREAM", "https://api.anthropic.com")


def forward_headers(request: Request) -> list[tuple[str, str]]:
    kept = [(k, v) for k, v in request.headers.items() if k.lower() not in _SKIP_REQUEST]
    kept.append(("accept-encoding", "identity"))
    return kept


@router.post("/v1/messages")
async def messages(request: Request) -> Response:
    return await _proxy(request, mirrored=True)


@router.post("/v1/messages/count_tokens")
async def count_tokens(request: Request) -> Response:
    return await _proxy(request)


@router.get("/v1/models")
async def models(request: Request) -> Response:
    return await _proxy(request)


def _api_error(message: str, status: int) -> JSONResponse:
    """AIRE's own failures wear Anthropic's error shape — the client parses this
    body with the same code it uses upstream, so it must not be a novel schema."""
    return JSONResponse({"type": "error", "error": {"type": "api_error", "message": message}},
                        status_code=status)


def _outfit(request: Request, headers: list[tuple[str, str]]) -> list[tuple[str, str]] | None:
    """Dress an identified caller's request for upstream. The AIRE key is shed
    (it must never reach Anthropic); if a credential of the caller's OWN
    survives, it rides — metered pass-through (#34), nothing lent. If nothing
    survives, the key is invited (#32) and AIRE lends, or answers plainly."""
    if tokens.identify(presented_token(request)) is not None:
        headers = [(k, v) for k, v in headers if k.lower() != "authorization"]
    if any(k.lower() in ("x-api-key", "authorization") for k, _ in headers):
        return headers
    return lending.lend(headers)


async def _proxy(request: Request, mirrored: bool = False) -> Response:
    body = await request.body()
    exchange = uuid.uuid4().hex
    holder = getattr(request.state, "holder", None)  # an invited key (#32), or nobody
    if mirrored:
        await gateway_mirror.log_request(exchange, request.headers, body,
                                         holder.nickname if holder else None)
    headers = forward_headers(request)
    if holder is not None:
        headers = _outfit(request, headers)
        if headers is None:
            lending.release(request.state)
            return _api_error("AIRE gateway: no credential to lend an invited key", 503)
    tap = (lambda status, ctype: ResponseTap(exchange, status, ctype, tokens.biller(holder))
           ) if mirrored else None
    return await forward(request, body, headers, _upstream(), tap, holder, _api_error)
