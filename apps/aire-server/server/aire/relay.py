"""The relay every wire shares (#30 Anthropic, #51 OpenAI): send the dressed
request upstream and stream its answer back as it arrives, byte for byte.

Only the admission, the credential and the price differ between the doors,
never the relay — so it lives once, here, below both routers. The mirror tap,
when a door hands one in, reads the same bytes on the side and never fails the
relay; the lending slot is returned here too, because the relay outlives the
frame that claimed it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import Response, StreamingResponse

from . import lending
from .gateway_mirror import ResponseTap

_SKIP_RESPONSE = {"content-length", "content-encoding", "transfer-encoding",
                  "connection", "date", "server"}
# The CLIENT owns the 300s silence watchdog and upstream pings feed it — the
# proxy's read timeout must be the last to fire, never the first.
_TIMEOUT = httpx.Timeout(connect=15.0, read=600.0, write=60.0, pool=15.0)


async def forward(request: Request, body: bytes, headers: list[tuple[str, str]], base: str,
                  tap_for: Any, holder: Any, error: Any) -> Response:
    """Send the dressed request to `base` and relay its answer as it arrives.
    Shared by every wire this daemon speaks (#30 Anthropic, #51 OpenAI): only the
    admission, the credential and the price differ between them, never the relay."""
    client = httpx.AsyncClient(base_url=base, timeout=_TIMEOUT)
    url = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    try:
        upstream = await client.send(
            client.build_request(request.method, url, content=body, headers=headers),
            stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        lending.release(request.state)
        return error(f"AIRE gateway: upstream unreachable ({type(exc).__name__})", 502)
    tap = tap_for(upstream.status_code, upstream.headers.get("content-type", "")) if tap_for else None
    out = {k: v for k, v in upstream.headers.items() if k.lower() not in _SKIP_RESPONSE}
    lending.hand_off(request.state)  # the relay outlives this frame and frees it
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
