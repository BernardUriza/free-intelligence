"""Shared debug-server infrastructure: app keys, auth, response helpers.

Everything the route handlers (and ``app.build_app``) need in common lives
here: the typed aiohttp app keys, the ``MoltbookDebugContext`` dataclass, the
small ``web.json_response`` shortcuts, and the bearer-auth middleware.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Any

from aiohttp import web

from personas.insult.core.contracts.memory import DebugMemoryPort


@dataclass
class MoltbookDebugContext:
    """Wires the OUTBOUND lane components into the debug server so the
    /debug/moltbook/* endpoints can preview drafts and force-post without
    waiting for the cron. None when MOLTBOOK_API_KEY is unset (the lane
    itself is fail-closed; the debug endpoints follow the same posture)."""

    source_factory: Any  # Callable[[], MoltbookSource | None]
    judge: Any  # RunnerJudgeClient | None
    settings: Any


# Typed aiohttp app keys (avoid NotAppKeyWarning). The memory key is typed by
# the structural DebugMemoryPort (the handlers' static view); the runtime tag is
# `object` so we don't import the concrete smart-side MemoryStore here — the
# store injected in app.py satisfies the port structurally.
_MEMORY_KEY: web.AppKey[DebugMemoryPort] = web.AppKey("memory", object)  # type: ignore[arg-type]
_TOKEN_KEY: web.AppKey[str] = web.AppKey("debug_token", str)
_MOLTBOOK_KEY: web.AppKey[MoltbookDebugContext | None] = web.AppKey("moltbook_ctx", object)  # type: ignore[arg-type]


def _unauthorized() -> web.Response:
    return web.json_response({"error": "unauthorized"}, status=401)


def _bad_request(msg: str) -> web.Response:
    return web.json_response({"error": msg}, status=400)


@web.middleware
async def _auth_middleware(request: web.Request, handler):
    # /debug/health is always public (liveness probe)
    if request.path == "/debug/health":
        return await handler(request)

    # /a/{id} is the public HTML artifact viewer. Anyone with the link
    # views the page. The artifact author (Insult agent) controls what
    # gets published; the link is itself the unguessable credential
    # (11 url-safe chars, ~64 bits). See html_artifacts.py.
    if request.path.startswith("/a/"):
        return await handler(request)

    # /sync/* uses per-user bearer tokens resolved against user_sync_tokens.
    # The handler does its own auth + stamps `request["sync_user_id"]` so
    # downstream code knows which Discord user is pushing data. This middleware
    # only validates that a Bearer header is present — the actual lookup
    # belongs to the handler so the constant-time DB query is part of the
    # authenticated path, not the open path.
    if request.path.startswith("/sync/"):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return _unauthorized()
        memory = request.app[_MEMORY_KEY]
        provided = header[len("Bearer ") :]
        user_id = await memory.resolve_sync_token(provided)
        if user_id is None:
            return _unauthorized()
        request["sync_user_id"] = user_id
        return await handler(request)

    expected_token = request.app[_TOKEN_KEY]
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return _unauthorized()
    provided = header[len("Bearer ") :]
    # Constant-time compare to resist timing side-channel
    if not hmac.compare_digest(provided, expected_token):
        return _unauthorized()
    return await handler(request)
