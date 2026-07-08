"""Debug HTTP server — read-only endpoints for inspecting bot state.

Exposes a small aiohttp app alongside the Discord bot so external tools
(including Claude Code) can read recent messages, channel activity, and
memory stats without touching Discord's API.

Security model:
- Fail-closed: if DEBUG_TOKEN is unset, the server does NOT start.
- All endpoints except /debug/health (+ the public /a/{id} viewer) require
  `Authorization: Bearer <token>`; /sync/* uses per-user bearer tokens.
- Binds to 127.0.0.1 by default. For production, gate via network boundary
  (Azure Container Apps without ingress is private by default).

This used to be one ~1075-line module; it's now a package split by concern:
- ``keys``      — app keys, auth middleware, response helpers
- ``health``    — /debug/health + the Postgres probe
- ``content``   — read-only inspection endpoints + arc reset + artifact viewer
- ``reminders`` — admin reminder CRUD
- ``sync``      — /sync/serenityops snapshot ingest
- ``app``       — build_app + start/stop lifecycle

This barrel re-exports the public surface so existing imports
(``from personas.insult.core.debug_server import build_app, ...``)
keep working unchanged.
"""

from personas.insult.core.debug_server.app import build_app, start_debug_server, stop_debug_server

__all__ = [
    "build_app",
    "start_debug_server",
    "stop_debug_server",
]
