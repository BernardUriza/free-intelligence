"""aiohttp app assembly + lifecycle for the debug server.

Wires the auth middleware, the app-key context (memory, token, moltbook),
and every route from the per-domain handler modules. ``build_app`` is the
single place the route table lives; ``start_debug_server`` / ``stop_debug_server``
own the runner lifecycle.
"""

from __future__ import annotations

import structlog
from aiohttp import web

from personas.insult.core.debug_server.content import (
    _handle_arc_reset,
    _handle_artifact_view,
    _handle_channels,
    _handle_costs,
    _handle_disclosure_list,
    _handle_facts,
    _handle_messages,
    _handle_stats,
)
from personas.insult.core.debug_server.health import _handle_health
from personas.insult.core.debug_server.keys import (
    _MEMORY_KEY,
    _MOLTBOOK_KEY,
    _TOKEN_KEY,
    MoltbookDebugContext,
    _auth_middleware,
)
from personas.insult.core.debug_server.moltbook import (
    _handle_moltbook_backfill,
    _handle_moltbook_engage,
    _handle_moltbook_engagement_draft,
    _handle_moltbook_engagement_preview,
    _handle_moltbook_feed,
    _handle_moltbook_post,
    _handle_moltbook_preview_outbound,
)
from personas.insult.core.debug_server.reminders import (
    _handle_create_reminder,
    _handle_delete_reminder,
    _handle_patch_reminder,
    _handle_reminders,
)
from personas.insult.core.debug_server.sync import _handle_sync_serenityops

log = structlog.get_logger()


def build_app(
    memory: object,
    debug_token: str,
    moltbook_ctx: MoltbookDebugContext | None = None,
) -> web.Application:
    """Construct the aiohttp Application with routes and middleware.

    `moltbook_ctx` is optional — when None the /debug/moltbook/* endpoints
    return 503. This lets the server start in deployments without a
    Moltbook key without leaking error spam at boot.

    ``memory`` is typed ``object`` on purpose: this host plumbing only stashes
    the store into the app under ``_MEMORY_KEY`` and never calls a method on it
    (the handlers retrieve it via that key, typed in ``keys.py``). Keeping the
    concrete smart-side ``MemoryStore`` out of this import is what the demux
    destilado is paying down. Don't re-add it."""
    app = web.Application(middlewares=[_auth_middleware])
    # type: ignore is strictly local and purely a type-checker concession: the
    # AppKey declares value type MemoryStore (in keys.py, decoupled separately),
    # and we hand it an `object`. This is a pass-through store — no runtime
    # dependency on MemoryStore's API exists here — so widening to object is
    # safe; only the AppKey's declared type disagrees.
    app[_MEMORY_KEY] = memory  # type: ignore[reportArgumentType]
    app[_TOKEN_KEY] = debug_token
    app[_MOLTBOOK_KEY] = moltbook_ctx
    app.router.add_get("/debug/health", _handle_health)
    app.router.add_get("/debug/messages", _handle_messages)
    app.router.add_get("/debug/channels", _handle_channels)
    app.router.add_get("/debug/stats", _handle_stats)
    app.router.add_get("/debug/disclosure", _handle_disclosure_list)
    app.router.add_post("/debug/arc/reset", _handle_arc_reset)
    app.router.add_get("/debug/reminders", _handle_reminders)
    app.router.add_post("/debug/reminders", _handle_create_reminder)
    app.router.add_delete("/debug/reminders/{id}", _handle_delete_reminder)
    app.router.add_patch("/debug/reminders/{id}", _handle_patch_reminder)
    app.router.add_get("/debug/moltbook/feed", _handle_moltbook_feed)
    app.router.add_get("/debug/moltbook/preview-outbound", _handle_moltbook_preview_outbound)
    app.router.add_post("/debug/moltbook/post", _handle_moltbook_post)
    app.router.add_post("/debug/moltbook/backfill", _handle_moltbook_backfill)
    app.router.add_get("/debug/moltbook/preview-engagement", _handle_moltbook_engagement_preview)
    app.router.add_get("/debug/moltbook/engagement-draft", _handle_moltbook_engagement_draft)
    app.router.add_post("/debug/moltbook/engage", _handle_moltbook_engage)
    app.router.add_get("/debug/costs", _handle_costs)
    app.router.add_get("/debug/facts", _handle_facts)
    app.router.add_post("/sync/serenityops", _handle_sync_serenityops)
    # Public HTML artifact viewer (no auth — id is the credential).
    app.router.add_get("/a/{id}", _handle_artifact_view)
    return app


async def start_debug_server(
    memory: object,
    debug_token: str,
    host: str = "127.0.0.1",
    port: int = 8787,
    moltbook_ctx: MoltbookDebugContext | None = None,
) -> web.AppRunner:
    """Start the debug server and return the runner for lifecycle management."""
    app = build_app(memory, debug_token, moltbook_ctx=moltbook_ctx)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    log.info("debug_server_started", host=host, port=port)
    return runner


async def stop_debug_server(runner: web.AppRunner) -> None:
    """Cleanly stop the debug server."""
    await runner.cleanup()
    log.info("debug_server_stopped")
