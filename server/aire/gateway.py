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
the mirror never fails the relay. Auth is pass-through (v1; per-consumer AIRE
tokens are backlog #28): the caller's own credential rides upstream, AIRE adds
none and stores none. This router sits BELOW the engine and never imports from
``engine/`` — serving it through the SDK would recurse (the spawned CLI calling
the daemon back).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from . import gateway_mirror
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


async def _proxy(request: Request, mirrored: bool = False) -> Response:
    body = await request.body()
    exchange = uuid.uuid4().hex
    if mirrored:
        await gateway_mirror.log_request(exchange, request.headers, body)
    client = httpx.AsyncClient(base_url=_upstream(), timeout=_TIMEOUT)
    url = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    try:
        upstream = await client.send(
            client.build_request(request.method, url, content=body,
                                 headers=_forward_headers(request)),
            stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        return JSONResponse(
            {"type": "error", "error": {"type": "api_error",
             "message": f"AIRE gateway: upstream unreachable ({type(exc).__name__})"}},
            status_code=502)
    tap = ResponseTap(exchange, upstream.status_code,
                      upstream.headers.get("content-type", "")) if mirrored else None
    headers = {k: v for k, v in upstream.headers.items() if k.lower() not in _SKIP_RESPONSE}
    return StreamingResponse(_relay(client, upstream, tap),
                             status_code=upstream.status_code, headers=headers)


async def _relay(client: httpx.AsyncClient, upstream: httpx.Response,
                 tap: ResponseTap | None) -> AsyncIterator[bytes]:
    try:
        async for chunk in upstream.aiter_raw():
            if tap is not None:
                tap.feed(chunk)
            yield chunk
    finally:
        if tap is not None:
            await tap.finish()
        await upstream.aclose()
        await client.aclose()
