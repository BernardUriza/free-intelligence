"""Engagement lane — Insult goes out to Moltbook, finds posts to argue
with, comments on them.

Distinct from `moltbook_outbound` (which posts new top-level content to
its own archive). Engagement adds Insult's voice into other agents'
conversations:

  1) extract_engagement_keywords(memory) — pull recent topics from
     world_scans (excluding the bot's own outbound rows). Returns 3-5
     short keywords ordered by recency.
  2) search_candidates(source, keywords, memory) — multi-search per
     keyword, dedupe, filter (own posts, stale, already-engaged).
  3) pick_target(candidates, persona, llm) — small LLM call: of these N
     posts, which would Insult actually have a real take on? returns
     index or None.
  4) build_engagement_comment(target, persona, llm) — short reply, 2-4
     sentences, English + California vulgar.
  5) regex_privacy_strip + redact_with_llm — same gates as outbound.
  6) source.create_comment(post.id, redacted) — auto-verifies via the
     v3.7.37 client wiring.
  7) persist_engagement(...) — world_scans row, source='moltbook_engagement',
     external_id = comment.id, commentary = post_id (so we can dedupe).

Hard gates (every cycle):
  • is_outbound_blocked → vulnerability + disclosure (same function as
    outbound; engagement is a public utterance too)
  • Empty redaction or substring leak → skip
  • LLM picks no candidate → skip silently
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass

import structlog

from insult.core.moltbook_outbound import (
    is_outbound_blocked,
    redact_with_llm,
    regex_privacy_strip,
)
from insult.core.prompts_loader import load_prompt
from insult.core.sources.base import Comment, Post

log = structlog.get_logger()

_ENGAGEMENT_SOURCE = "moltbook_engagement"
_KEYWORD_MAX = 5
_MIN_KEYWORD_LEN = 4
_PER_KEYWORD_LIMIT = 5
_POST_STALENESS_DAYS = 5
_MAX_PICK_CANDIDATES = 8


_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "about",
        "from",
        "this",
        "that",
        "those",
        "these",
        "your",
        "their",
        "what",
        "where",
        "when",
        "which",
        "into",
        "over",
        "under",
        "between",
        "como",
        "para",
        "sobre",
        "entre",
        "tiene",
        "tienes",
        "donde",
        "cuando",
        "cual",
        "que",
        "porque",
        "esto",
        "esta",
        "estos",
        "estas",
        "moltbook",
        "outbound",
        "inbound",
    }
)


@dataclass
class EngagementCandidate:
    post: Post
    keyword: str  # which search keyword surfaced this post


@dataclass
class EngagementResult:
    target: EngagementCandidate
    comment_text: str  # post-redaction, what got published
    comment_text_pre_redaction: str
    comment_id: str
    comment_url: str | None


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------


def _tokenize_topic(topic: str) -> list[str]:
    """Split a world_scan topic string into engagement-worthy keywords.
    Drops stopwords, short tokens, and pure-digit tokens."""
    tokens = re.findall(r"[a-zA-Z][a-zA-Z\-']{3,}", topic.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) >= _MIN_KEYWORD_LEN]


async def extract_engagement_keywords(memory, *, max_keywords: int = _KEYWORD_MAX) -> list[str]:
    """Build a keyword list from the bot's recent world observations.

    Sources we pull from:
      • world_scans (any source except moltbook_outbound* — those are our
        own posts and would feed the bot back to itself)

    We deduplicate while preserving recency order. The first occurrence
    of each token wins."""
    seen: dict[str, None] = {}
    rows = await memory.get_recent_world_scans(limit=40)
    for row in rows:
        src = str(row.get("source", ""))
        if src.startswith("moltbook_"):
            continue
        topic = str(row.get("topic", ""))
        for tok in _tokenize_topic(topic):
            if tok not in seen:
                seen[tok] = None
                if len(seen) >= max_keywords:
                    return list(seen.keys())
    return list(seen.keys())


# ---------------------------------------------------------------------------
# Candidate search + filter
# ---------------------------------------------------------------------------


async def _already_engaged_post_ids(memory) -> set[str]:
    """Return the set of post_ids the bot has commented on previously.
    We store post_id in the world_scan `commentary` field of engagement
    rows so this lookup is a single read of recent engagement rows."""
    rows = await memory.get_recent_world_scans(limit=50, source=_ENGAGEMENT_SOURCE)
    out: set[str] = set()
    for row in rows:
        commentary = str(row.get("commentary", ""))
        # commentary format: "post_id=<id> ..."
        m = re.search(r"post_id=([\w-]+)", commentary)
        if m:
            out.add(m.group(1))
    return out


async def search_candidates(
    source,
    keywords: list[str],
    memory,
    *,
    own_author_name: str = "insultmx",
    per_keyword: int = _PER_KEYWORD_LIMIT,
) -> list[EngagementCandidate]:
    """Multi-search across keywords; return deduped candidates after
    filtering own posts, stale posts, and already-engaged posts."""
    if not keywords:
        return []
    already = await _already_engaged_post_ids(memory)
    cutoff = time.time() - _POST_STALENESS_DAYS * 86400
    seen_ids: set[str] = set()
    out: list[EngagementCandidate] = []
    for kw in keywords:
        try:
            posts = await source.search_posts(kw, limit=per_keyword)
        except Exception:
            log.exception("moltbook_engagement_search_failed", keyword=kw)
            continue
        for post in posts:
            if not post.id or post.id in seen_ids or post.id in already:
                continue
            if (post.author or "").lower() == own_author_name.lower():
                continue
            # STRICT staleness: if we can't read the created_at we don't
            # know how old the post is — reject. Better to skip than to
            # comment on a 6-month-old archive thread.
            if not post.created_at or post.created_at < cutoff:
                continue
            seen_ids.add(post.id)
            out.append(EngagementCandidate(post=post, keyword=kw))
    # Newest first — Insult should engage with current threads, not archives.
    out.sort(key=lambda c: c.post.created_at, reverse=True)
    return out


# ---------------------------------------------------------------------------
# Target selection — small LLM call
# ---------------------------------------------------------------------------


async def pick_target(
    candidates: list[EngagementCandidate],
    *,
    persona: str,
    llm,
    model: str | None = None,
) -> EngagementCandidate | None:
    """Of N candidates, ask the LLM which ONE Insult would actually engage
    with. The LLM returns either an index 0..N-1 or 'none' if no post
    deserves a comment.

    Trimming: cap candidates at 8 to keep the prompt cheap."""
    if not candidates:
        return None
    pool = candidates[:_MAX_PICK_CANDIDATES]
    listing = "\n".join(
        f"[{i}] keyword={c.keyword} | author={c.post.author} | submolt={c.post.submolt}\n"
        f"    title: {c.post.title[:140]}\n"
        f"    excerpt: {c.post.content[:300].replace(chr(10), ' ')}"
        for i, c in enumerate(pool)
    )
    system = f"{persona[:1500]}\n\n{load_prompt('moltbook_engagement_target')}"
    user = f"Candidate posts (one per block):\n\n{listing}\n\nReturn JSON only."
    try:
        resp = (
            await llm.chat(system, [{"role": "user", "content": user}], model=model)
            if model
            else await llm.chat(system, [{"role": "user", "content": user}])
        )
        raw = (resp.text or "").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(raw)
    except Exception:
        log.exception("moltbook_engagement_pick_failed")
        return None

    pick = data.get("pick")
    if pick == "none" or pick is None:
        log.info("moltbook_engagement_pick_none", candidate_count=len(pool))
        return None
    try:
        idx = int(pick)
    except (TypeError, ValueError):
        log.warning("moltbook_engagement_pick_bad_index", pick=pick)
        return None
    if not 0 <= idx < len(pool):
        log.warning("moltbook_engagement_pick_out_of_range", pick=idx, n=len(pool))
        return None
    return pool[idx]


# ---------------------------------------------------------------------------
# Comment drafting — second LLM call
# ---------------------------------------------------------------------------


async def build_engagement_comment(
    candidate: EngagementCandidate,
    *,
    persona: str,
    llm,
    model: str | None = None,
) -> str | None:
    """Generate a short engagement comment for the chosen post.
    Returns the raw draft (pre-redaction) or None on failure."""
    system = f"{persona[:1500]}\n\n{load_prompt('moltbook_engagement_comment')}"
    user = (
        f"Target post:\n"
        f"  author: {candidate.post.author}\n"
        f"  submolt: {candidate.post.submolt}\n"
        f"  title: {candidate.post.title}\n\n"
        f"  body:\n{candidate.post.content[:2000]}\n\n"
        f"Write the comment now."
    )
    try:
        resp = (
            await llm.chat(system, [{"role": "user", "content": user}], model=model)
            if model
            else await llm.chat(system, [{"role": "user", "content": user}])
        )
        text = (resp.text or "").strip()
    except Exception:
        log.exception("moltbook_engagement_comment_call_failed")
        return None
    if not text:
        log.info("moltbook_engagement_comment_empty")
        return None
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return text


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


async def persist_engagement(
    candidate: EngagementCandidate,
    redacted_comment: str,
    comment_id: str,
    *,
    memory,
) -> None:
    """Record the engagement so it counts toward dedupe + Discord narration."""
    try:
        await memory.store_world_scan(
            topic=f"comment on: {candidate.post.title[:140]}",
            findings=redacted_comment[:1000],
            commentary=f"post_id={candidate.post.id} keyword={candidate.keyword}",
            source=_ENGAGEMENT_SOURCE,
            external_id=comment_id,
        )
    except Exception:
        log.exception("moltbook_engagement_persist_failed", comment_id=comment_id)


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


async def engage_once(
    *,
    source,
    memory,
    persona: str,
    llm,
    summary_model: str,
    facts_user_ids: list[str],
    channel_id: str | None = None,
    dry_run: bool = False,
) -> EngagementResult | tuple[None, str]:
    """Run one engagement pass. Returns:
      • EngagementResult on successful publish
      • (None, reason) on every short-circuit (gate failure, no candidate,
        redaction blocked, etc.) — caller logs and moves on

    `dry_run=True` runs through draft + privacy + redaction but stops
    before create_comment + persist. Used by the debug preview endpoint."""
    blocked, blocked_uid = await is_outbound_blocked(facts_user_ids, memory=memory, channel_id=channel_id)
    if blocked:
        return None, f"{blocked}:{blocked_uid}"

    keywords = await extract_engagement_keywords(memory)
    if not keywords:
        return None, "no_keywords"

    candidates = await search_candidates(source, keywords, memory)
    if not candidates:
        return None, "no_candidates"

    target = await pick_target(candidates, persona=persona, llm=llm)
    if target is None:
        return None, "pick_none"

    draft = await build_engagement_comment(target, persona=persona, llm=llm)
    if not draft:
        return None, "draft_empty"
    # SKIP detection: the prompt says to return SKIP standalone, but in
    # practice the model sometimes appends it after a paragraph it couldn't
    # commit to. Treat any draft whose final line is exactly SKIP as a
    # skip — that line is the model's last decision.
    final_line = draft.strip().splitlines()[-1].strip().upper() if draft.strip() else ""
    if final_line == "SKIP" or draft.strip().upper() == "SKIP":
        log.info(
            "moltbook_engagement_skipped_by_prompt",
            post_id=target.post.id,
            draft_preview=draft[:200],
        )
        return None, "draft_skip_token"

    # Aggregate facts across the relevant users for redaction
    all_facts: list[str] = []
    for uid in facts_user_ids:
        facts = await memory.get_facts(uid)
        all_facts.extend(f["fact"] for f in facts)
    stripped = regex_privacy_strip(draft, [{"fact": f} for f in all_facts])
    redacted = await redact_with_llm(stripped, all_facts, client=llm.client, model=summary_model)
    if redacted is None:
        return None, "redaction_blocked"

    if dry_run:
        return EngagementResult(
            target=target,
            comment_text=redacted,
            comment_text_pre_redaction=draft,
            comment_id="",
            comment_url=None,
        )

    try:
        comment: Comment = await source.create_comment(target.post.id, redacted)
    except Exception:
        log.exception(
            "moltbook_engagement_publish_failed",
            post_id=target.post.id,
            keyword=target.keyword,
        )
        return None, "publish_failed"

    await persist_engagement(target, redacted, comment.id, memory=memory)
    log.info(
        "moltbook_engagement_published",
        comment_id=comment.id,
        post_id=target.post.id,
        keyword=target.keyword,
    )
    return EngagementResult(
        target=target,
        comment_text=redacted,
        comment_text_pre_redaction=draft,
        comment_id=comment.id,
        comment_url=None,
    )
