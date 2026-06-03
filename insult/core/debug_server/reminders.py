"""Admin reminder endpoints — escape hatch when the LLM tool flow breaks.

list (GET) + create (POST) + delete (DELETE) + patch (PATCH). These bypass
the create_reminder tool flow so an operator can fix reminders directly
without a roundtrip through the LLM.
"""

from __future__ import annotations

import structlog
from aiohttp import web

from insult.core.debug_server.keys import _MEMORY_KEY, _bad_request
from insult.core.reminders import parse_remind_at

log = structlog.get_logger()


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
            requires_ack=bool(payload.get("requires_ack", False)),
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
