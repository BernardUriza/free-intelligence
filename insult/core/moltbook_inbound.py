"""Moltbook INBOUND lane — bring curated posts back to Discord.

Read-only path: fetch from Moltbook submolts, dedupe against world_scans,
rank by overlap with what Insult observes about its users, render an
in-character commentary message, persist what was shown.

Vulnerability gate is the first thing the entrypoint checks. If ANY user
in the channel scores at or above VULNERABLE_THRESHOLD, the whole inbound
flow is paused — content from external agent networks is the wrong thing
to bring into a chat where someone is in crisis. The preset/persona side
already handles this; we mirror the same posture here.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import structlog

from insult.core.prompts_loader import load_prompt
from insult.core.sources.base import Post, Source, SourceError
from insult.core.vulnerability import is_vulnerable_user

log = structlog.get_logger()


# Words shorter than this are skipped when scoring overlap — too noisy
# (es/en stopwords mostly).
_MIN_SIGNIFICANT_WORD_LEN = 4
# How many posts to bring back per submolt before ranking the union.
_DEFAULT_FETCH_PER_SUBMOLT = 5
# How many curated picks to ultimately show in a single digest message.
_DEFAULT_KEEP_TOP = 3
# Recency: posts older than this are treated as zero-recency.
_RECENCY_HORIZON_HOURS = 24.0


# ---------------------------------------------------------------------------
# Result dataclass — surfaced to the caller for logging / dashboards
# ---------------------------------------------------------------------------


@dataclass
class InboundDigestResult:
    picks: list[Post] = field(default_factory=list)
    rendered_message: str | None = None
    skipped_reason: str | None = None  # 'no_submolts' / 'vulnerability_gate' / etc.


# ---------------------------------------------------------------------------
# Step 1 — fetch + dedupe
# ---------------------------------------------------------------------------


async def fetch_inbound_digest(
    source: Source,
    submolts: list[str],
    *,
    memory,
    limit_per_submolt: int = _DEFAULT_FETCH_PER_SUBMOLT,
) -> list[Post]:
    """Fetch top posts from each configured submolt, drop anything we have
    already shown to users (lookup `world_scans.has_external_id`), and
    return the union for ranking."""
    fresh: list[Post] = []
    seen_ids: set[str] = set()  # in-memory dedupe within a single call too
    for submolt in submolts:
        try:
            posts = await source.fetch_submolt_posts(submolt, sort="hot", limit=limit_per_submolt)
        except SourceError as e:
            log.warning("moltbook_inbound_fetch_failed", submolt=submolt, error=str(e))
            continue
        for p in posts:
            if not p.id or p.id in seen_ids:
                continue
            if await memory.has_external_id(source.name, p.id):
                continue
            seen_ids.add(p.id)
            fresh.append(p)
    log.info("moltbook_inbound_fetched", total=len(fresh), submolts=len(submolts))
    return fresh


# ---------------------------------------------------------------------------
# Step 2 — rank by overlap with observed user context
# ---------------------------------------------------------------------------


def _significant_words(text: str) -> set[str]:
    """Lowercase split keeping only alphanumeric tokens of length ≥ MIN."""
    out: set[str] = set()
    for raw in text.lower().split():
        token = "".join(c for c in raw if c.isalnum())
        if len(token) >= _MIN_SIGNIFICANT_WORD_LEN:
            out.add(token)
    return out


def rank_for_users(
    posts: list[Post],
    user_context_text: str,
    *,
    keep_top: int = _DEFAULT_KEEP_TOP,
    now: float | None = None,
) -> list[Post]:
    """Rank posts against the union of user facts + recent message context.

    Score = 2.0 * keyword_overlap_count
          + recency_score (0..1, decaying over RECENCY_HORIZON_HOURS)
          + engagement_score (upvotes / 100, capped at 2.0)

    The 2.0 weight on overlap is deliberate: relevance to what users care
    about should beat a viral post nobody-here-cares-about every time.
    Recency and engagement are tie-breakers, not the primary signal."""
    if not posts:
        return []
    context_words = _significant_words(user_context_text)
    if not context_words:
        # No user context at all — fall back to recency + engagement only
        return sorted(posts, key=lambda p: (p.created_at, p.upvotes), reverse=True)[:keep_top]
    ts = now or time.time()
    scored: list[tuple[float, Post]] = []
    for p in posts:
        overlap = len(_significant_words(f"{p.title} {p.content}") & context_words)
        recency = 0.0
        if p.created_at > 0:
            age_hours = (ts - p.created_at) / 3600.0
            recency = max(0.0, _RECENCY_HORIZON_HOURS - age_hours) / _RECENCY_HORIZON_HOURS
        engagement = min(p.upvotes / 100.0, 2.0)
        scored.append((overlap * 2.0 + recency + engagement, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for score, p in scored[:keep_top] if score > 0]


# ---------------------------------------------------------------------------
# Step 3 — render to Discord via the LLM
# ---------------------------------------------------------------------------


# Prompt lives in insult/prompts/moltbook_inbound_render.md


async def render_digest_message(
    picks: list[Post],
    *,
    judge,
    settings,
) -> str | None:
    """Send picks through the runner's one-shot /v1/judge with the Moltbook
    overlay on top of the base persona (handed in as the system prompt).
    Returns the in-character commentary, or None if the call came back
    empty / failed (caller should log + skip)."""
    if not picks:
        return None
    posts_block = "\n\n".join(
        f"### {p.title}\n[{p.submolt}] by {p.author} · {p.upvotes} upvotes\n{p.content[:500]}" for p in picks
    )
    prompt = (
        f"{settings.system_prompt[:2000]}\n\n"
        f"{load_prompt('moltbook_inbound_render')}\n\n"
        f"## Posts encontrados\n{posts_block}"
    )
    try:
        resp = await judge.utility_call(prompt, [{"role": "user", "content": "Comenta lo que viste."}])
        text = (resp.text or "").strip()
        return text or None
    except Exception:
        log.exception("moltbook_inbound_render_failed", picks=len(picks))
        return None


# ---------------------------------------------------------------------------
# Step 4 — persist what was shown so we don't show it again
# ---------------------------------------------------------------------------


async def persist_picks(picks: list[Post], commentary: str, *, memory, source_name: str = "moltbook") -> int:
    """Write each pick to world_scans with source + external_id so the next
    inbound run dedupes them out via has_external_id. Returns the number
    of NEW rows actually inserted (already-seen rows are no-ops thanks to
    the partial UNIQUE index)."""
    inserted = 0
    for p in picks:
        wrote = await memory.store_world_scan(
            topic=f"[{p.submolt}] {p.title}",
            findings=p.content[:1000],
            commentary=commentary[:1000],
            source=source_name,
            external_id=p.id,
        )
        if wrote:
            inserted += 1
    return inserted


# ---------------------------------------------------------------------------
# Top-level entrypoint
# ---------------------------------------------------------------------------


async def build_inbound_digest(
    source: Source,
    submolts: list[str],
    user_ids: list[str],
    *,
    memory,
    judge,
    settings,
    recent_messages: list[dict] | None = None,
) -> InboundDigestResult:
    """Drive the whole inbound pipeline end-to-end.

    Order is gated for safety:
      1. No submolts configured → bail
      2. ANY user vulnerable → bail (don't pump external content into a
         chat where someone is in crisis)
      3. Fetch from each submolt, dedupe against world_scans
      4. Rank by overlap with users' fact store + recent messages
      5. Render in-character commentary via LLM
      6. Persist picks (so future runs dedupe them)
    """
    if not submolts:
        log.info("moltbook_inbound_skipped", reason="no_submolts")
        return InboundDigestResult(skipped_reason="no_submolts")

    # Vulnerability gate — reused from the preset/persona pipeline
    for uid in user_ids:
        facts = await memory.get_facts(uid)
        if is_vulnerable_user(facts):
            log.info("moltbook_inbound_skipped", reason="vulnerability_gate", user_id=uid)
            return InboundDigestResult(skipped_reason="vulnerability_gate")

    posts = await fetch_inbound_digest(source, submolts, memory=memory)
    if not posts:
        log.info("moltbook_inbound_skipped", reason="no_posts_after_dedupe")
        return InboundDigestResult(skipped_reason="no_posts_after_dedupe")

    # Build context blob: facts of all users + recent messages
    context_parts: list[str] = []
    for uid in user_ids:
        facts = await memory.get_facts(uid)
        context_parts.extend(f["fact"] for f in facts)
    if recent_messages:
        context_parts.extend(m.get("content", "") for m in recent_messages[-15:])
    context_text = " ".join(context_parts)

    picks = rank_for_users(posts, context_text)
    if not picks:
        log.info("moltbook_inbound_skipped", reason="no_relevant_after_rank", candidate_count=len(posts))
        return InboundDigestResult(skipped_reason="no_relevant_after_rank")

    rendered = await render_digest_message(picks, judge=judge, settings=settings)
    if not rendered:
        log.warning("moltbook_inbound_skipped", reason="render_empty", picks=len(picks))
        return InboundDigestResult(picks=picks, skipped_reason="render_empty")

    # Persist BEFORE returning — caller will use rendered_message to send
    # to Discord, and we want dedupe state to reflect what was actually
    # surfaced (even if Discord send fails after this point, the user
    # already saw or will see it).
    await persist_picks(picks, rendered, memory=memory)

    log.info(
        "moltbook_inbound_digest_built",
        picks=len(picks),
        rendered_len=len(rendered),
        submolts=len(submolts),
    )
    return InboundDigestResult(picks=picks, rendered_message=rendered)
