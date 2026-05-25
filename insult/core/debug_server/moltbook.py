"""/debug/moltbook/* — preview + manual-override endpoints for the Moltbook lanes.

feed/preview-outbound/preview-engagement/engagement-draft are inspection
surfaces (run the pipeline, don't publish); post/engage/backfill are the
manual write overrides, each guarded by a preview-hash echo so a stale draft
can't be replayed. All 503 when the Moltbook context isn't configured.
"""

from __future__ import annotations

import hashlib
import hmac

import structlog
from aiohttp import web

from insult.core.debug_server.keys import _MEMORY_KEY, _MOLTBOOK_KEY, _bad_request

log = structlog.get_logger()


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
        judge=ctx.judge,
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
    redacted = await redact_with_llm(stripped, all_facts, judge=ctx.judge, model=ctx.settings.summary_model)
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


async def _handle_moltbook_engagement_preview(request: web.Request) -> web.Response:
    """GET /debug/moltbook/preview-engagement?channel_id=X — runs the
    engagement pipeline through draft + redaction WITHOUT publishing.
    Returns the chosen target post, the redacted comment, and a hash you'd
    echo back to /engage to actually publish."""
    from insult.core.moltbook_engagement import engage_once

    ctx = request.app[_MOLTBOOK_KEY]
    if ctx is None:
        return _moltbook_unconfigured()
    source = ctx.source_factory()
    if source is None:
        return _moltbook_unconfigured()
    memory = request.app[_MEMORY_KEY]
    channel_id = request.query.get("channel_id")
    if not channel_id:
        return _bad_request("channel_id required")
    recent = await memory.get_recent(channel_id, limit=15)
    user_ids = list({m["user_id"] for m in recent if m.get("role") == "user" and m.get("user_id")})
    result = await engage_once(
        source=source,
        memory=memory,
        persona=ctx.settings.system_prompt,
        judge=ctx.judge,
        summary_model=ctx.settings.summary_model,
        facts_user_ids=user_ids,
        channel_id=channel_id,
        dry_run=True,
        blocked_authors=ctx.settings.moltbook_blocked_authors,
    )
    if not isinstance(result, tuple):
        # EngagementResult on success
        target = result.target
        preview_hash = _draft_hash("engagement", result.comment_text, target.post.id)
        return web.json_response(
            {
                "target_post_id": target.post.id,
                "target_title": target.post.title,
                "target_author": target.post.author,
                "target_submolt": target.post.submolt,
                "keyword": target.keyword,
                "comment": result.comment_text,
                "comment_pre_redaction": result.comment_text_pre_redaction,
                "preview_hash": preview_hash,
            }
        )
    # On skip, surface enough state to diagnose: the keyword pool we
    # extracted and how many raw candidates each keyword surfaced before
    # the dedupe/staleness/already-engaged filter.
    from insult.core.moltbook_engagement import (
        _already_engaged_post_ids,
        extract_engagement_keywords,
    )

    keywords = await extract_engagement_keywords(memory)
    already = await _already_engaged_post_ids(memory)
    per_keyword: list[dict] = []
    for kw in keywords:
        try:
            posts = await source.search_posts(kw, limit=5)
            per_keyword.append({"keyword": kw, "raw_count": len(posts), "ids": [p.id for p in posts]})
        except Exception as e:
            per_keyword.append({"keyword": kw, "error": str(e)[:200]})
    return web.json_response(
        {
            "skipped_reason": result[1],
            "keywords": keywords,
            "already_engaged_ids": list(already),
            "search_per_keyword": per_keyword,
        },
        status=200,
    )


async def _handle_moltbook_engagement_draft(request: web.Request) -> web.Response:
    """GET /debug/moltbook/engagement-draft?post_id=X&channel_id=Y — fetch
    a specific Moltbook post, run Insult's engagement comment LLM against
    it, apply privacy gates + redaction, return the draft + preview_hash.
    Used to test an engagement comment on a post you choose, bypassing
    the keyword search + pick_target stages."""
    from insult.core.moltbook_engagement import (
        EngagementCandidate,
        build_engagement_comment,
    )
    from insult.core.moltbook_outbound import (
        is_outbound_blocked,
        redact_with_llm,
        regex_privacy_strip,
    )

    ctx = request.app[_MOLTBOOK_KEY]
    if ctx is None:
        return _moltbook_unconfigured()
    source = ctx.source_factory()
    if source is None:
        return _moltbook_unconfigured()
    memory = request.app[_MEMORY_KEY]
    post_id = request.query.get("post_id")
    channel_id = request.query.get("channel_id")
    if not post_id or not channel_id:
        return _bad_request("post_id and channel_id required")

    try:
        # Use search to fetch the post: Moltbook's GET /posts/<id> returns
        # `{success, post}` so we'd need a separate _post_from_json path.
        # Search by id isn't supported, so we hit the API directly.
        import aiohttp

        url = f"{ctx.settings.moltbook_base_url}/posts/{post_id}"
        api_key = ctx.settings.moltbook_api_key.get_secret_value()
        async with (
            aiohttp.ClientSession() as s,
            s.get(url, headers={"Authorization": f"Bearer {api_key}"}) as r,
        ):
            data = await r.json()
        post_data = data.get("post") or {}
        if not post_data:
            return web.json_response({"error": "post not found", "raw": data}, status=404)
        from insult.core.sources.moltbook import MoltbookSource

        post = MoltbookSource._post_from_json(post_data)
    except Exception as e:
        log.exception("moltbook_engagement_draft_fetch_failed")
        return web.json_response({"error": f"fetch failed: {e}"}, status=502)

    # Privacy gates
    recent = await memory.get_recent(channel_id, limit=15)
    user_ids = list({m["user_id"] for m in recent if m.get("role") == "user" and m.get("user_id")})
    blocked, blocked_uid = await is_outbound_blocked(user_ids, memory=memory, channel_id=channel_id)
    if blocked:
        return web.json_response({"skipped_reason": blocked, "blocked_user_id": blocked_uid}, status=200)

    # Force the candidate (skip keyword search + pick_target)
    candidate = EngagementCandidate(post=post, keyword="(forced)")
    draft = await build_engagement_comment(candidate, persona=ctx.settings.system_prompt, judge=ctx.judge)
    if not draft:
        return web.json_response({"skipped_reason": "draft_empty"}, status=200)
    final_line = draft.strip().splitlines()[-1].strip().upper() if draft.strip() else ""
    if final_line == "SKIP" or draft.strip().upper() == "SKIP":
        return web.json_response(
            {"skipped_reason": "draft_skip_token", "draft": draft},
            status=200,
        )

    all_facts: list[str] = []
    for uid in user_ids:
        facts = await memory.get_facts(uid)
        all_facts.extend(f["fact"] for f in facts)
    stripped = regex_privacy_strip(draft, [{"fact": f} for f in all_facts])
    redacted = await redact_with_llm(stripped, all_facts, judge=ctx.judge, model=ctx.settings.summary_model)
    if redacted is None:
        return web.json_response(
            {"skipped_reason": "redaction_blocked", "draft": draft},
            status=200,
        )

    preview_hash = _draft_hash("engagement", redacted, post.id)
    return web.json_response(
        {
            "target_post_id": post.id,
            "target_title": post.title,
            "target_author": post.author,
            "target_submolt": post.submolt,
            "comment": redacted,
            "comment_pre_redaction": draft,
            "preview_hash": preview_hash,
        }
    )


async def _handle_moltbook_engage(request: web.Request) -> web.Response:
    """POST /debug/moltbook/engage — manual override that publishes a
    pre-approved engagement comment. Body needs target_post_id + comment +
    preview_hash. Same hash-echo pattern as /post."""
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
    target_post_id = payload.get("target_post_id")
    comment = payload.get("comment")
    preview_hash = payload.get("preview_hash")
    parent_id = payload.get("parent_id")  # optional, for threaded replies
    if not all(isinstance(x, str) and x for x in (target_post_id, comment, preview_hash)):
        return _bad_request("target_post_id, comment, preview_hash are required strings")
    expected = _draft_hash("engagement", comment, target_post_id)
    if not hmac.compare_digest(preview_hash, expected):
        return web.json_response(
            {"error": "preview_hash mismatch — re-run /preview-engagement"},
            status=409,
        )
    try:
        kwargs = {"parent_id": parent_id} if isinstance(parent_id, str) and parent_id else {}
        c = await source.create_comment(target_post_id, comment, **kwargs)
    except Exception as e:
        log.exception("moltbook_engagement_admin_publish_failed")
        return web.json_response({"error": f"publish failed: {e}"}, status=502)

    memory = request.app[_MEMORY_KEY]
    try:
        await memory.store_world_scan(
            topic=f"comment on post: {target_post_id[:36]}",
            findings=comment[:1000],
            commentary=f"post_id={target_post_id} (manual)",
            source="moltbook_engagement",
            external_id=c.id,
        )
    except Exception:
        log.exception("moltbook_engagement_admin_persist_failed", comment_id=c.id)
    log.info("moltbook_engagement_admin_published", comment_id=c.id, target_post_id=target_post_id)
    return web.json_response({"comment_id": c.id, "published": True})


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
