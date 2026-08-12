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
AIRE adds none and stores none. The exception is an INVITED key (#32), which by
construction has no Anthropic credential — for those callers AIRE lends its own
(``lending``) and bills the turn against that key's ceiling (``pricing``), since
Anthropic reports tokens and a ceiling needs dollars. That is the one path where
this door spends AIRE's money.

This router sits BELOW the engine and never imports from ``engine/`` — serving
it through the SDK would recurse (the spawned CLI calling the daemon back).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from . import gateway_mirror, lending, pricing, tokens
from .gateway_mirror import ResponseTap

router = APIRouter()

# Hop-by-hop and transport headers are the proxy's own business; everything
# else — anthropic-version, anthropic-beta (never allowlisted), x-claude-code-*
# — forwards verbatim. x-aire-project is addressed to AIRE, consumed here.
# accept-encoding is forced to identity so the relayed bytes are the SSE text
# itself (the mirror tap must read them), never a gzip frame.
_SKIP_REQUEST = {"host", "content-length", "connection", "keep-alive", "te",
                 "trailer", "transfer-encoding", "upgrade", "proxy-authenticate",
                 "proxy-authorization", "accept-encoding", "x-aire-project"}
_SKIP_RESPONSE = {"content-length", "content-encoding", "transfer-encoding",
                  "connection", "date", "server"}

# The CLIENT owns the 300s silence watchdog and upstream pings feed it — the
# proxy's read timeout must be the last to fire, never the first.
_TIMEOUT = httpx.Timeout(connect=15.0, read=600.0, write=60.0, pool=15.0)


def _upstream() -> str:
    return os.environ.get("AIRE_GATEWAY_UPSTREAM", "https://api.anthropic.com")


def _forward_headers(request: Request) -> list[tuple[str, str]]:
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


def _biller(holder: Any) -> Any:
    """How an invited turn pays for the credential AIRE lent it. A real turn
    that prices at $0 is PRINTED, never swallowed: that is exactly what a
    ceiling looks like while it is not biting, and it stayed invisible once."""
    if holder is None:
        return None

    async def bank(usage: dict[str, Any] | None, model: str) -> None:
        cost = pricing.usd(usage, model)
        if cost <= 0:
            print(f"INVITE {holder.nickname}: a relayed turn banked $0 "
                  f"(model={model!r}) — the ceiling is not biting", flush=True)
        await tokens.charge(holder.nickname, cost)

    return bank


async def _proxy(request: Request, mirrored: bool = False) -> Response:
    body = await request.body()
    exchange = uuid.uuid4().hex
    holder = getattr(request.state, "holder", None)  # an invited key (#32), or nobody
    if mirrored:
        await gateway_mirror.log_request(exchange, request.headers, body)
    headers = _forward_headers(request)
    if holder is not None:
        headers = lending.lend(headers)
        if headers is None:
            lending.leave(holder.nickname)
            return _api_error("AIRE gateway: no credential to lend an invited key", 503)
    client = httpx.AsyncClient(base_url=_upstream(), timeout=_TIMEOUT)
    url = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    try:
        upstream = await client.send(
            client.build_request(request.method, url, content=body, headers=headers),
            stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        if holder is not None:
            lending.leave(holder.nickname)
        return _api_error(f"AIRE gateway: upstream unreachable ({type(exc).__name__})", 502)
    tap = ResponseTap(exchange, upstream.status_code,
                      upstream.headers.get("content-type", ""),
                      _biller(holder)) if mirrored else None
    out = {k: v for k, v in upstream.headers.items() if k.lower() not in _SKIP_RESPONSE}
    return StreamingResponse(_relay(client, upstream, tap, holder),
                             status_code=upstream.status_code, headers=out)


async def _relay(client: httpx.AsyncClient, upstream: httpx.Response,
                 tap: ResponseTap | None, holder: Any = None) -> AsyncIterator[bytes]:
    try:
        async for chunk in upstream.aiter_raw():
            if tap is not None:
                tap.feed(chunk)
            yield chunk
    finally:
        if tap is not None:
            await tap.finish()
        if holder is not None:  # the slot frees even when the socket died mid-turn
            lending.leave(holder.nickname)
        await upstream.aclose()
        await client.aclose()
