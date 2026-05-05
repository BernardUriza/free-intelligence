"""Debug HTTP server — read-only endpoints for inspecting bot state.

Exposes a small aiohttp app alongside the Discord bot so external tools
(including Claude Code) can read recent messages, channel activity, and
memory stats without touching Discord's API.

Security model:
- Fail-closed: if DEBUG_TOKEN is unset, the server does NOT start.
- All endpoints except /debug/health require `Authorization: Bearer <token>`.
- Binds to 0.0.0.0 by default. For production, gate via network boundary
  (Azure Container Apps without ingress is private by default).

All endpoints are read-only EXCEPT:
  • `POST /debug/reminders` — admin escape hatch when the LLM's
    create_reminder tool flow is broken (see v3.7.3 commit).
  • `POST /debug/moltbook/post` — manual override for OUTBOUND posting,
    requires a preview-hash echo so a stale draft can't be published
    by accident. See v3.7.23 / Phase 5 of the carretera plan.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any

import structlog
from aiohttp import web

from insult.core.memory import MemoryStore
from insult.core.reminders import parse_remind_at

log = structlog.get_logger()


@dataclass
class MoltbookDebugContext:
    """Wires the OUTBOUND lane components into the debug server so the
    /debug/moltbook/* endpoints can preview drafts and force-post without
    waiting for the cron. None when MOLTBOOK_API_KEY is unset (the lane
    itself is fail-closed; the debug endpoints follow the same posture)."""

    source_factory: Any  # Callable[[], MoltbookSource | None]
    llm: Any
    settings: Any


# Typed aiohttp app keys (avoid NotAppKeyWarning)
_MEMORY_KEY: web.AppKey[MemoryStore] = web.AppKey("memory", MemoryStore)
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
    db = await memory._disclosure._conn()
    cursor = await db.execute(
        "SELECT timestamp, channel_id, category, severity, message_excerpt "
        "FROM disclosure_log WHERE user_id = ? AND timestamp >= ? "
        "ORDER BY timestamp DESC LIMIT 50",
        (user_id, since),
    )
    rows = await cursor.fetchall()
    return web.json_response(
        {
            "user_id": user_id,
            "days": days,
            "count": len(rows),
            "rows": [
                {
                    "timestamp": r[0],
                    "channel_id": r[1],
                    "category": r[2],
                    "severity": r[3],
                    "excerpt": r[4],
                }
                for r in rows
            ],
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


def _moltbook_unconfigured() -> web.Response:
    return web.json_response(
        {"error": "moltbook source not configured (api_key empty or context missing)"},
        status=503,
    )


def _draft_hash(title: str, content: str, submolt: str) -> str:
    """Stable hash of the parts an operator would echo back to publish.

    The hash is for accident prevention, not adversarial defense — the
    Bearer token guards against unauthorized callers; this guards against
    'I copied an old preview into my publish call.'"""
    blob = f"{submolt}\x00{title}\x00{content}".encode()
    return hashlib.sha256(blob).hexdigest()[:16]


async def _handle_moltbook_feed(request: web.Request) -> web.Response:
    """Preview what Insult would see if it ran an inbound fetch right now.
    No LLM calls, no curation, no Discord side-effects — just the raw
    posts the source returns."""
    ctx = request.app[_MOLTBOOK_KEY]
    if ctx is None:
        return _moltbook_unconfigured()
    source = ctx.source_factory()
    if source is None:
        return _moltbook_unconfigured()
    submolt = request.query.get("submolt")
    try:
        limit = int(request.query.get("limit", "10"))
    except ValueError:
        return _bad_request("limit must be an integer")
    if limit < 1 or limit > 25:
        return _bad_request("limit must be between 1 and 25")

    try:
        if submolt:
            posts = await source.fetch_submolt_posts(submolt, sort="hot", limit=limit)
        else:
            posts = await source.fetch_feed(sort="hot", limit=limit)
    except Exception as e:
        return web.json_response({"error": f"fetch failed: {e}"}, status=502)

    return web.json_response(
        {
            "submolt": submolt,
            "count": len(posts),
            "posts": [
                {
                    "id": p.id,
                    "title": p.title,
                    "content": p.content[:500],
                    "author": p.author,
                    "submolt": p.submolt,
                    "upvotes": p.upvotes,
                    "comment_count": p.comment_count,
                    "url": p.url,
                }
                for p in posts
            ],
        }
    )


async def _handle_moltbook_preview_outbound(request: web.Request) -> web.Response:
    """Run the OUTBOUND pipeline against the bot's current memory but DON'T
    publish. Returns the draft, redaction result, gate status, and a
    preview_hash the operator must echo back to actually publish.

    This is the inspection surface required before flipping
    MOLTBOOK_OUTBOUND_ENABLED=true in prod."""
    from insult.core.moltbook_outbound import (
        assign_subject_codes,
        build_post_draft,
        detect_salience_signal,
        is_outbound_blocked,
        load_previous_outbound_notes,
        persist_draft,
        redact_with_llm,
        regex_privacy_strip,
    )

    ctx = request.app[_MOLTBOOK_KEY]
    if ctx is None:
        return _moltbook_unconfigured()
    if ctx.source_factory() is None:
        return _moltbook_unconfigured()
    if not ctx.settings.moltbook_submolts:
        return _bad_request("moltbook_submolts is empty")

    channel_id = request.query.get("channel_id")
    if not channel_id:
        return _bad_request("channel_id is required")
    memory = request.app[_MEMORY_KEY]
    recent = await memory.get_recent(channel_id, limit=15)
    user_ids = list({m["user_id"] for m in recent if m.get("role") == "user" and m.get("user_id")})
    if not user_ids:
        return web.json_response({"skipped_reason": "no_users_in_channel"}, status=200)

    blocked_reason, blocked_uid = await is_outbound_blocked(user_ids, memory=memory, channel_id=channel_id)
    if blocked_reason:
        return web.json_response({"skipped_reason": blocked_reason, "blocked_user_id": blocked_uid}, status=200)

    signal = await detect_salience_signal(channel_id, user_ids, memory=memory, recent_messages=recent)
    if signal is None:
        return web.json_response({"skipped_reason": "no_salience"}, status=200)

    target_submolt = ctx.settings.moltbook_submolts[0]
    previous_notes = await load_previous_outbound_notes(memory, limit=5)
    subject_codes = assign_subject_codes(user_ids)
    draft = await build_post_draft(
        signal,
        target_submolt,
        persona=ctx.settings.system_prompt,
        llm=ctx.llm,
        previous_notes=previous_notes,
        subject_codes=subject_codes,
    )
    if draft is None:
        return web.json_response({"skipped_reason": "draft_failed"}, status=200)

    all_facts: list[str] = []
    for uid in user_ids:
        facts = await memory.get_facts(uid)
        all_facts.extend(f["fact"] for f in facts)
    stripped = regex_privacy_strip(draft.content, [{"fact": f} for f in all_facts])
    redacted = await redact_with_llm(stripped, all_facts, client=ctx.llm.client, model=ctx.settings.summary_model)
    if redacted is None:
        # Persist the blocked draft for audit even though it won't go out
        await persist_draft(draft, None, memory=memory, extra_notes="preview_redaction_blocked")
        return web.json_response(
            {"skipped_reason": "redaction_failed_or_leaked", "draft_title": draft.title}, status=200
        )

    # Audit: every preview goes to the DB. Operator can review later even
    # if they don't immediately POST it.
    await persist_draft(draft, redacted, memory=memory, extra_notes="preview")

    preview_hash = _draft_hash(draft.title, redacted, target_submolt)
    return web.json_response(
        {
            "salience_kind": signal.kind,
            "salience_topic": signal.topic,
            "submolt": target_submolt,
            "title": draft.title,
            "content": redacted,
            "regex_stripped": stripped,
            "draft_pre_redaction": draft.content,
            "preview_hash": preview_hash,
            "facts_count": len(all_facts),
            "user_ids": user_ids,
        }
    )


async def _handle_moltbook_backfill(request: web.Request) -> web.Response:
    """POST /debug/moltbook/backfill — record an externally-published post in
    the local world_scans table without re-publishing. Used to retro-import
    posts created before the persistence wiring was complete."""
    memory = request.app[_MEMORY_KEY]
    try:
        payload = await request.json()
    except (ValueError, TypeError):
        return _bad_request("body must be valid JSON")
    title = payload.get("title")
    content = payload.get("content", "")
    submolt = payload.get("submolt", "")
    external_id = payload.get("external_id")
    if not isinstance(title, str) or not title or not isinstance(external_id, str) or not external_id:
        return _bad_request("title and external_id required")
    await memory.store_world_scan(
        topic=title,
        findings=str(content)[:1000],
        commentary=f"published submolt={submolt} (backfill)",
        source="moltbook_outbound",
        external_id=external_id,
    )
    return web.json_response({"backfilled": True, "external_id": external_id})


async def _handle_moltbook_post(request: web.Request) -> web.Response:
    """Force-publish a draft to Moltbook. Body must include preview_hash
    matching the hash of (title, content, submolt) so a stale draft from
    a previous preview-outbound call can't be replayed."""
    ctx = request.app[_MOLTBOOK_KEY]
    if ctx is None:
        return _moltbook_unconfigured()
    source = ctx.source_factory()
    if source is None:
        return _moltbook_unconfigured()

    try:
        payload = await request.json()
    except (ValueError, TypeError):
        return _bad_request("body must be valid JSON")

    title = payload.get("title")
    content = payload.get("content")
    submolt = payload.get("submolt")
    preview_hash = payload.get("preview_hash")
    if not all(isinstance(x, str) and x for x in (title, content, submolt, preview_hash)):
        return _bad_request("title, content, submolt, preview_hash are required strings")

    expected_hash = _draft_hash(title, content, submolt)
    if not hmac.compare_digest(preview_hash, expected_hash):
        log.warning("moltbook_post_hash_mismatch", expected=expected_hash, got=preview_hash[:16])
        return web.json_response(
            {"error": "preview_hash mismatch — re-run /preview-outbound and copy the fresh hash"},
            status=409,
        )

    try:
        post = await source.create_post(submolt, title, content)
    except Exception as e:
        log.exception("moltbook_post_publish_failed")
        return web.json_response({"error": f"publish failed: {e}"}, status=502)

    memory = request.app[_MEMORY_KEY]
    try:
        await memory.store_world_scan(
            topic=title,
            findings=content[:1000],
            commentary=f"published submolt={submolt} (manual)",
            source="moltbook_outbound",
            external_id=post.id,
        )
    except Exception:
        log.exception("moltbook_post_persist_failed", post_id=post.id)

    log.info("moltbook_post_admin_published", post_id=post.id, submolt=submolt, title=title)
    return web.json_response(
        {
            "id": post.id,
            "submolt": post.submolt or submolt,
            "url": post.url,
            "published": True,
        },
        status=201,
    )


async def _handle_costs(_request: web.Request) -> web.Response:
    from insult.core.llm import get_usage_report

    return web.json_response(get_usage_report())


def build_app(
    memory: MemoryStore,
    debug_token: str,
    moltbook_ctx: MoltbookDebugContext | None = None,
) -> web.Application:
    """Construct the aiohttp Application with routes and middleware.

    `moltbook_ctx` is optional — when None the /debug/moltbook/* endpoints
    return 503. This lets the server start in deployments without a
    Moltbook key without leaking error spam at boot."""
    app = web.Application(middlewares=[_auth_middleware])
    app[_MEMORY_KEY] = memory
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
    app.router.add_get("/debug/costs", _handle_costs)
    return app


async def start_debug_server(
    memory: MemoryStore,
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
