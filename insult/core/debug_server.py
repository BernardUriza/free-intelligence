"""Debug HTTP server — read-only endpoints for inspecting bot state.

Exposes a small aiohttp app alongside the Discord bot so external tools
(including Claude Code) can read recent messages, channel activity, and
memory stats without touching Discord's API.

Security model:
- Fail-closed: if DEBUG_TOKEN is unset, the server does NOT start.
- All endpoints except /debug/health require `Authorization: Bearer <token>`.
- Binds to 0.0.0.0 by default. For production, gate via network boundary
  (Azure Container Apps without ingress is private by default).

All endpoints are read-only EXCEPT `POST /debug/reminders` — see that
handler for the carve-out. The write path exists because when the LLM's
`create_reminder` tool flow is broken (e.g. tool schema rejected by the
API, fallback strips all tools), the user has no in-band way to recover
a reminder request and the bot silently ate it. The admin-side POST is
the manual escape hatch.
"""

from __future__ import annotations

import hmac

import structlog
from aiohttp import web

from insult.core.memory import MemoryStore
from insult.core.reminders import parse_remind_at

log = structlog.get_logger()

# Typed aiohttp app keys (avoid NotAppKeyWarning)
_MEMORY_KEY: web.AppKey[MemoryStore] = web.AppKey("memory", MemoryStore)
_TOKEN_KEY: web.AppKey[str] = web.AppKey("debug_token", str)


def _unauthorized() -> web.Response:
    return web.json_response({"error": "unauthorized"}, status=401)


def _bad_request(msg: str) -> web.Response:
    return web.json_response({"error": msg}, status=400)


@web.middleware
async def _auth_middleware(request: web.Request, handler):
    # /debug/health is always public (liveness probe)
    if request.path == "/debug/health":
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


async def _handle_health(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def _handle_messages(request: web.Request) -> web.Response:
    channel_id = request.query.get("channel_id")
    if not channel_id:
        return _bad_request("channel_id is required")

    try:
        limit = int(request.query.get("limit", "15"))
    except ValueError:
        return _bad_request("limit must be an integer")
    if limit < 1 or limit > 500:
        return _bad_request("limit must be between 1 and 500")

    memory = request.app[_MEMORY_KEY]
    messages = await memory.get_recent(channel_id, limit=limit)
    return web.json_response({"channel_id": channel_id, "count": len(messages), "messages": messages})


async def _handle_channels(request: web.Request) -> web.Response:
    memory = request.app[_MEMORY_KEY]
    guild_id = request.query.get("guild_id")

    # If no guild_id, return overview of all channels across all guilds
    if not guild_id:
        try:
            limit = int(request.query.get("limit", "50"))
        except ValueError:
            return _bad_request("limit must be an integer")
        if limit < 1 or limit > 500:
            return _bad_request("limit must be between 1 and 500")
        channels = await memory.get_channels_overview(limit=limit)
        return web.json_response({"count": len(channels), "channels": channels})

    try:
        since_hours = float(request.query.get("since_hours", "24"))
    except ValueError:
        return _bad_request("since_hours must be a number")

    import time as _time

    since_ts = _time.time() - (since_hours * 3600)
    activity = await memory.get_channel_activity_since(guild_id, since_ts)
    return web.json_response(
        {"guild_id": guild_id, "since_hours": since_hours, "count": len(activity), "channels": activity}
    )


async def _handle_stats(request: web.Request) -> web.Response:
    memory = request.app[_MEMORY_KEY]
    stats = await memory.get_stats()
    return web.json_response(stats)


async def _handle_reminders(request: web.Request) -> web.Response:
    memory = request.app[_MEMORY_KEY]
    channel_id = request.query.get("channel_id")

    if channel_id:
        reminders = await memory.get_channel_reminders(channel_id)
    else:
        # All pending reminders across all channels
        import time as _time

        reminders = await memory.get_pending_reminders(_time.time() + 86400 * 365)  # 1yr horizon

    return web.json_response({"count": len(reminders), "reminders": reminders})


async def _handle_create_reminder(request: web.Request) -> web.Response:
    """Admin write path — insert a reminder bypassing the LLM tool flow.

    Body (JSON):
      - channel_id (str, required)
      - description (str, required)
      - remind_at (str ISO 8601 with tz offset, required) — e.g. "2026-05-04T08:00:00-06:00"
      - guild_id (str, optional)
      - created_by (str, optional, default "admin")
      - mention_user_ids (list[str] | str CSV, optional)
      - recurring (str, optional, one of: none|daily|weekly|monthly, default "none")
    """
    try:
        payload = await request.json()
    except (ValueError, TypeError):
        return _bad_request("body must be valid JSON")

    channel_id = payload.get("channel_id")
    description = payload.get("description")
    remind_at_iso = payload.get("remind_at")
    if not channel_id or not description or not remind_at_iso:
        return _bad_request("channel_id, description, and remind_at are required")

    remind_at = parse_remind_at(remind_at_iso)
    if remind_at is None:
        return _bad_request("remind_at must be a future ISO 8601 datetime with tz offset")

    recurring = payload.get("recurring", "none")
    if recurring not in {"none", "daily", "weekly", "monthly"}:
        return _bad_request("recurring must be one of: none, daily, weekly, monthly")

    mention_raw = payload.get("mention_user_ids", "")
    mention_user_ids = ",".join(str(x) for x in mention_raw) if isinstance(mention_raw, list) else str(mention_raw)

    memory = request.app[_MEMORY_KEY]
    try:
        reminder_id = await memory.save_reminder(
            channel_id=str(channel_id),
            guild_id=str(payload["guild_id"]) if payload.get("guild_id") else None,
            created_by=str(payload.get("created_by", "admin")),
            description=str(description),
            remind_at=remind_at,
            mention_user_ids=mention_user_ids,
            recurring=recurring,
        )
    except Exception as e:  # surface all DB errors to the admin caller
        log.error("debug_create_reminder_failed", error=str(e))
        return web.json_response({"error": f"save failed: {e}"}, status=500)

    return web.json_response(
        {
            "id": reminder_id,
            "channel_id": channel_id,
            "description": description,
            "remind_at": remind_at,
            "recurring": recurring,
        },
        status=201,
    )


async def _handle_delete_reminder(request: web.Request) -> web.Response:
    """Admin write path — delete a not-yet-delivered reminder by id.

    Returns 404 if the row doesn't exist or was already delivered. Used to
    clean up duplicates / mistakes when fixing them via Discord chat would
    cost a roundtrip with the LLM.
    """
    raw_id = request.match_info.get("id", "")
    try:
        reminder_id = int(raw_id)
    except ValueError:
        return _bad_request("id must be an integer")

    memory = request.app[_MEMORY_KEY]
    deleted = await memory.delete_reminder(reminder_id)
    if not deleted:
        return web.json_response({"error": "not found or already delivered"}, status=404)
    return web.json_response({"id": reminder_id, "deleted": True})


async def _handle_patch_reminder(request: web.Request) -> web.Response:
    """Admin write path — update remind_at and/or description of a pending reminder.

    Body (JSON): any subset of `{remind_at, description}`. At least one
    field must be present and non-null. `remind_at` accepts the same
    ISO 8601 + tz format as POST.
    """
    raw_id = request.match_info.get("id", "")
    try:
        reminder_id = int(raw_id)
    except ValueError:
        return _bad_request("id must be an integer")

    try:
        payload = await request.json()
    except (ValueError, TypeError):
        return _bad_request("body must be valid JSON")

    new_remind_at: float | None = None
    if "remind_at" in payload and payload["remind_at"] is not None:
        new_remind_at = parse_remind_at(str(payload["remind_at"]))
        if new_remind_at is None:
            return _bad_request("remind_at must be a future ISO 8601 datetime with tz offset")

    new_description: str | None = None
    if "description" in payload and payload["description"] is not None:
        desc = str(payload["description"]).strip()
        if not desc:
            return _bad_request("description cannot be empty")
        new_description = desc

    if new_remind_at is None and new_description is None:
        return _bad_request("at least one of remind_at, description is required")

    memory = request.app[_MEMORY_KEY]
    changed = await memory.update_reminder_fields(
        reminder_id,
        new_remind_at=new_remind_at,
        new_description=new_description,
    )
    if not changed:
        return web.json_response({"error": "not found or already delivered"}, status=404)
    return web.json_response(
        {
            "id": reminder_id,
            "updated": True,
            "remind_at": new_remind_at,
            "description": new_description,
        }
    )


async def _handle_costs(_request: web.Request) -> web.Response:
    from insult.core.llm import get_usage_report

    return web.json_response(get_usage_report())


def build_app(memory: MemoryStore, debug_token: str) -> web.Application:
    """Construct the aiohttp Application with routes and middleware."""
    app = web.Application(middlewares=[_auth_middleware])
    app[_MEMORY_KEY] = memory
    app[_TOKEN_KEY] = debug_token
    app.router.add_get("/debug/health", _handle_health)
    app.router.add_get("/debug/messages", _handle_messages)
    app.router.add_get("/debug/channels", _handle_channels)
    app.router.add_get("/debug/stats", _handle_stats)
    app.router.add_get("/debug/reminders", _handle_reminders)
    app.router.add_post("/debug/reminders", _handle_create_reminder)
    app.router.add_delete("/debug/reminders/{id}", _handle_delete_reminder)
    app.router.add_patch("/debug/reminders/{id}", _handle_patch_reminder)
    app.router.add_get("/debug/costs", _handle_costs)
    return app


async def start_debug_server(
    memory: MemoryStore,
    debug_token: str,
    host: str = "127.0.0.1",
    port: int = 8787,
) -> web.AppRunner:
    """Start the debug server and return the runner for lifecycle management."""
    app = build_app(memory, debug_token)
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
