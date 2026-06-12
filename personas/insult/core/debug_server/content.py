"""Read-only inspection endpoints + the arc-reset escape hatch.

messages / channels / stats / disclosure / facts / costs are pure reads;
arc/reset is the one write here (force a stuck CRISIS arc back to STABILITY);
the /a/{id} artifact viewer streams stored HTML verbatim (public, no auth).
"""

from __future__ import annotations

from aiohttp import web

from personas.insult.core.debug_server.keys import _MEMORY_KEY, _bad_request


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


async def _handle_disclosure_list(request: web.Request) -> web.Response:
    """GET /debug/disclosure?user_id=X&days=14 — list disclosure_log rows."""
    memory = request.app[_MEMORY_KEY]
    user_id = request.query.get("user_id")
    if not user_id:
        return _bad_request("user_id required")
    try:
        days = int(request.query.get("days", "14"))
    except ValueError:
        return _bad_request("days must be int")
    import time as _time

    since = _time.time() - days * 86400
    rows = await memory.list_disclosures(user_id, since)
    return web.json_response(
        {
            "user_id": user_id,
            "days": days,
            "count": len(rows),
            "rows": rows,
        }
    )


async def _handle_arc_reset(request: web.Request) -> web.Response:
    """POST /debug/arc/reset?channel_id=X&user_id=Y — force STABILITY.

    Used to break out of stuck CRISIS state caused by historical bugs in the
    arc transition logic. Body/query: channel_id, user_id. Returns the prior
    arc and the new one.
    """
    memory = request.app[_MEMORY_KEY]
    channel_id = request.query.get("channel_id")
    user_id = request.query.get("user_id")
    if not channel_id or not user_id:
        return _bad_request("channel_id and user_id required")
    import time as _time

    prior = await memory.get_arc(channel_id, user_id)
    await memory.upsert_arc(channel_id, user_id, "stability", _time.time(), 0, 0, 0)
    new = await memory.get_arc(channel_id, user_id)
    return web.json_response({"prior": prior, "new": new})


async def _handle_costs(_request: web.Request) -> web.Response:
    from personas.insult.core.llm import get_usage_report

    return web.json_response(get_usage_report())


async def _handle_facts(request: web.Request) -> web.Response:
    """GET /debug/facts?user_id=X — list the user's long-term fact rows.

    Used to verify what the bot actually knows about a participant when
    a "memory bug" report comes in. Cross-references the chat (what the
    user says they told the bot) with the DB (what's actually in the
    fact store). See .claude/rules/testing.md § "Inspect the database
    BEFORE believing the chat" for the diagnostic workflow.

    Added on 2026-05-12 after a CV-recovery session where the assistant
    needed to know which of Alex's facts had been extracted (vs which
    only lived in the messages table). The endpoint exists so future
    incidents don't require running scripts against the blob to read
    the fact store.
    """
    memory = request.app[_MEMORY_KEY]
    user_id = request.query.get("user_id")
    if not user_id:
        return _bad_request("user_id required")
    facts = await memory.get_facts(user_id)
    return web.json_response({"user_id": user_id, "count": len(facts), "facts": facts})


async def _handle_artifact_view(request: web.Request) -> web.Response:
    """Public viewer for agent-published HTML artifacts.

    No auth — the unguessable 11-char id IS the credential. See
    `_auth_middleware` for the /a/ bypass and `html_artifacts.py` for
    the storage layer.
    """
    from personas.insult.core.html_artifacts import get_artifact

    artifact_id = request.match_info.get("id", "")
    if not artifact_id or len(artifact_id) > 64 or "/" in artifact_id:
        return web.Response(
            text="<!DOCTYPE html><title>404</title><h1>Not found</h1>",
            content_type="text/html",
            status=404,
        )
    artifact = await get_artifact(artifact_id)
    if artifact is None:
        return web.Response(
            text="<!DOCTYPE html><title>404</title><h1>Not found</h1><p>This artifact does not exist or was removed.</p>",
            content_type="text/html",
            status=404,
        )
    # Stream the stored HTML verbatim. The agent owns the full document
    # (DOCTYPE, head, body) — we don't wrap or transform anything.
    return web.Response(
        text=artifact["html_content"],
        content_type="text/html",
        charset="utf-8",
    )
