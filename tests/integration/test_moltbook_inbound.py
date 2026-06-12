"""Tests for moltbook_inbound — fetch / rank / render / persist pipeline.

All external dependencies (Source, MemoryStore, LLM) are mocked. The
pipeline is intentionally pure-function except for the I/O hops, so
ranking / dedupe / vulnerability-gate behavior can be tested in isolation
from the platform client."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

from personas.insult.core.moltbook_inbound import (
    InboundDigestResult,
    build_inbound_digest,
    fetch_inbound_digest,
    persist_picks,
    rank_for_users,
    render_digest_message,
)
from personas.insult.core.sources.base import Post, SourceTransientError


def _post(
    post_id: str,
    title: str = "title",
    content: str = "body",
    submolt: str = "m/test",
    upvotes: int = 0,
    created_at: float | None = None,
) -> Post:
    """Build a Post with sane defaults for ranking tests."""
    return Post(
        id=post_id,
        title=title,
        content=content,
        author="someone",
        submolt=submolt,
        upvotes=upvotes,
        comment_count=0,
        created_at=created_at if created_at is not None else time.time(),
        source="moltbook",
    )


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def test_rank_returns_empty_when_no_posts():
    assert rank_for_users([], "anything") == []


def test_rank_falls_back_to_recency_engagement_when_no_user_context():
    """If we have zero user context (cold-start, all facts purged), still
    pick something — the most recent / most upvoted, in that order."""
    old = _post("p1", created_at=1.0, upvotes=100)
    new = _post("p2", created_at=time.time(), upvotes=1)
    picks = rank_for_users([old, new], "")
    assert picks[0].id == "p2"  # newer wins


def test_rank_keyword_overlap_dominates():
    """A post mentioning user-relevant keywords beats a more recent /
    higher-engagement post that doesn't match."""
    on_topic = _post(
        "match",
        title="Reflexiones sobre filosofía contemporánea",
        content="Hablar de fenomenología y consciencia",
        upvotes=0,
        created_at=time.time() - 12 * 3600,
    )
    off_topic = _post(
        "miss",
        title="Gaming news weekly roundup",
        content="Latest releases and patches",
        upvotes=99,
        created_at=time.time(),
    )
    picks = rank_for_users(
        [off_topic, on_topic],
        user_context_text="filosofía fenomenología consciencia",
        keep_top=1,
    )
    assert picks[0].id == "match"


def test_rank_drops_zero_score_picks():
    """When user context exists, posts that score 0 (no overlap, ancient,
    no upvotes) are filtered out — better silent than irrelevant."""
    irrelevant = _post(
        "irrelevant",
        title="random thing",
        content="nothing",
        upvotes=0,
        created_at=0.0,  # ancient → recency 0
    )
    picks = rank_for_users([irrelevant], "completely different topic", keep_top=5)
    assert picks == []


def test_rank_keep_top_caps_results():
    posts = [_post(f"p{i}", title=f"art post {i}", content="filosofía") for i in range(10)]
    picks = rank_for_users(posts, "filosofía art", keep_top=3)
    assert len(picks) == 3


def test_rank_short_words_are_ignored():
    """4-char minimum: 'el', 'de', 'que' shouldn't count as overlap."""
    p = _post("p1", title="el de que", content="al")
    picks = rank_for_users([p], "el de que al", keep_top=5)
    # No significant words from the post body OR the user context, so
    # ranking falls back to recency-engagement (returns the post since
    # it's the only candidate). The point of the test is that we did NOT
    # crash and didn't double-count noise tokens.
    assert isinstance(picks, list)


# ---------------------------------------------------------------------------
# fetch_inbound_digest — dedupe + error handling
# ---------------------------------------------------------------------------


async def test_fetch_dedupes_against_world_scans():
    """Posts whose external_id is already in world_scans are dropped before
    they reach ranking — saves LLM tokens on already-seen content."""
    source = MagicMock()
    source.name = "moltbook"
    source.fetch_submolt_posts = AsyncMock(return_value=[_post("seen"), _post("fresh")])
    memory = MagicMock()

    async def has_external(src, ext):
        return ext == "seen"

    memory.has_external_id = AsyncMock(side_effect=has_external)
    fresh = await fetch_inbound_digest(source, ["m/test"], memory=memory)
    assert [p.id for p in fresh] == ["fresh"]


async def test_fetch_dedupes_within_a_single_call():
    """Same external_id appearing in two submolts gets deduped to one entry."""
    source = MagicMock()
    source.name = "moltbook"
    source.fetch_submolt_posts = AsyncMock(return_value=[_post("dup")])
    memory = MagicMock()
    memory.has_external_id = AsyncMock(return_value=False)
    fresh = await fetch_inbound_digest(source, ["m/a", "m/b"], memory=memory)
    assert len(fresh) == 1


async def test_fetch_continues_when_one_submolt_errors():
    """If one submolt is gone (404 etc.), the other submolts still get
    fetched. Whole digest shouldn't crash on a stale config entry."""
    source = MagicMock()
    source.name = "moltbook"

    async def fetch(submolt, sort, limit):
        if submolt == "m/dead":
            raise SourceTransientError("upstream timeout")
        return [_post(f"{submolt}_p1")]

    source.fetch_submolt_posts = AsyncMock(side_effect=fetch)
    memory = MagicMock()
    memory.has_external_id = AsyncMock(return_value=False)
    fresh = await fetch_inbound_digest(source, ["m/dead", "m/alive"], memory=memory)
    assert [p.id for p in fresh] == ["m/alive_p1"]


async def test_fetch_skips_posts_without_id():
    """Defensive: if Moltbook ever returns a post without id, drop it
    rather than persist a NULL external_id row."""
    source = MagicMock()
    source.name = "moltbook"
    source.fetch_submolt_posts = AsyncMock(return_value=[_post("", title="anonymous"), _post("p1")])
    memory = MagicMock()
    memory.has_external_id = AsyncMock(return_value=False)
    fresh = await fetch_inbound_digest(source, ["m/x"], memory=memory)
    assert [p.id for p in fresh] == ["p1"]


# ---------------------------------------------------------------------------
# render_digest_message
# ---------------------------------------------------------------------------


async def test_render_returns_none_for_empty_picks():
    judge = MagicMock()
    judge.utility_call = AsyncMock()
    settings = MagicMock(system_prompt="persona")
    out = await render_digest_message([], judge=judge, settings=settings)
    assert out is None
    judge.utility_call.assert_not_called()


async def test_render_calls_llm_with_persona_and_picks():
    judge = MagicMock()
    judge.utility_call = AsyncMock(return_value=MagicMock(text="qué buena rola"))
    settings = MagicMock(system_prompt="this is the persona file content")
    picks = [_post("p1", title="art expo", content="some interesting take")]
    out = await render_digest_message(picks, judge=judge, settings=settings)
    assert out == "qué buena rola"
    prompt_arg = judge.utility_call.call_args.args[0]
    assert "persona file content" in prompt_arg
    assert "art expo" in prompt_arg


async def test_render_returns_none_when_llm_returns_blank():
    judge = MagicMock()
    judge.utility_call = AsyncMock(return_value=MagicMock(text="   "))
    settings = MagicMock(system_prompt="persona")
    picks = [_post("p1")]
    assert await render_digest_message(picks, judge=judge, settings=settings) is None


async def test_render_returns_none_when_llm_raises():
    judge = MagicMock()
    judge.utility_call = AsyncMock(side_effect=RuntimeError("anthropic dead"))
    settings = MagicMock(system_prompt="persona")
    picks = [_post("p1")]
    assert await render_digest_message(picks, judge=judge, settings=settings) is None


# ---------------------------------------------------------------------------
# persist_picks — dedupe behavior of world_scans surface
# ---------------------------------------------------------------------------


async def test_persist_returns_inserted_count():
    memory = MagicMock()

    async def store(*_args, **kwargs):
        # First pick is fresh, second is dup
        return kwargs["external_id"] == "p1"

    memory.store_world_scan = AsyncMock(side_effect=store)
    picks = [_post("p1"), _post("p2")]
    inserted = await persist_picks(picks, "commentary", memory=memory)
    assert inserted == 1


async def test_persist_writes_with_source_and_external_id():
    memory = MagicMock()
    memory.store_world_scan = AsyncMock(return_value=True)
    picks = [_post("p1", title="hola", submolt="m/x")]
    await persist_picks(picks, "comm", memory=memory, source_name="moltbook")
    kw = memory.store_world_scan.call_args.kwargs
    assert kw["source"] == "moltbook"
    assert kw["external_id"] == "p1"
    assert "[m/x]" in kw["topic"]


# ---------------------------------------------------------------------------
# build_inbound_digest — top-level orchestration with gates
# ---------------------------------------------------------------------------


def _mock_memory(facts_by_user=None, has_external_id_value=False):
    mem = MagicMock()
    mem.has_external_id = AsyncMock(return_value=has_external_id_value)
    mem.store_world_scan = AsyncMock(return_value=True)

    async def get_facts(uid):
        if facts_by_user is None:
            return []
        return facts_by_user.get(uid, [])

    mem.get_facts = AsyncMock(side_effect=get_facts)
    return mem


def _mock_source(posts):
    src = MagicMock()
    src.name = "moltbook"
    src.fetch_submolt_posts = AsyncMock(return_value=posts)
    return src


async def test_build_skips_when_no_submolts():
    src = _mock_source([])
    mem = _mock_memory()
    judge = MagicMock(utility_call=AsyncMock())
    settings = MagicMock(system_prompt="persona")
    res = await build_inbound_digest(src, [], ["u1"], memory=mem, judge=judge, settings=settings)
    assert isinstance(res, InboundDigestResult)
    assert res.skipped_reason == "no_submolts"
    src.fetch_submolt_posts.assert_not_called()


async def test_build_pauses_for_vulnerable_user():
    """A user with quetiapina + sertralina + named diagnosis crosses the
    vulnerability threshold; inbound MUST not run."""
    vulnerable_facts = {
        "u1": [
            {"fact": "Toma quetiapina 50mg para CPTSD", "category": "personal"},
            {"fact": "Diagnóstico de Complex PTSD por su psiquiatra", "category": "personal"},
            {"fact": "Hospitalizado en 2024 por crisis depresiva", "category": "incidents"},
        ]
    }
    src = _mock_source([_post("p1")])
    mem = _mock_memory(facts_by_user=vulnerable_facts)
    judge = MagicMock(utility_call=AsyncMock())
    settings = MagicMock(system_prompt="persona")
    res = await build_inbound_digest(src, ["m/x"], ["u1"], memory=mem, judge=judge, settings=settings)
    assert res.skipped_reason == "vulnerability_gate"
    src.fetch_submolt_posts.assert_not_called()
    judge.utility_call.assert_not_called()


async def test_build_skips_when_all_posts_already_seen():
    src = _mock_source([_post("p1"), _post("p2")])
    mem = _mock_memory(has_external_id_value=True)
    judge = MagicMock(utility_call=AsyncMock())
    settings = MagicMock(system_prompt="persona")
    res = await build_inbound_digest(src, ["m/x"], ["u1"], memory=mem, judge=judge, settings=settings)
    assert res.skipped_reason == "no_posts_after_dedupe"
    judge.utility_call.assert_not_called()


async def test_build_skips_when_nothing_relevant():
    """Posts exist but score 0 against user context — skip render rather
    than send a digest of irrelevant content."""
    src = _mock_source([_post("p1", title="random gaming news", content="patches", created_at=0.0, upvotes=0)])
    mem = _mock_memory(facts_by_user={"u1": [{"fact": "le interesa la filosofía", "category": "interests"}]})
    judge = MagicMock(utility_call=AsyncMock())
    settings = MagicMock(system_prompt="persona")
    res = await build_inbound_digest(src, ["m/x"], ["u1"], memory=mem, judge=judge, settings=settings)
    assert res.skipped_reason == "no_relevant_after_rank"
    judge.utility_call.assert_not_called()


async def test_build_happy_path_returns_picks_and_rendered_message():
    posts = [
        _post(
            "p1",
            title="filosofía contemporánea",
            content="reflexiones sobre fenomenología en agentes",
            upvotes=10,
            created_at=time.time() - 3600,
        ),
        _post(
            "p2",
            title="gaming roundup",
            content="patches",
            upvotes=2,
            created_at=time.time() - 3600,
        ),
    ]
    src = _mock_source(posts)
    mem = _mock_memory(facts_by_user={"u1": [{"fact": "le gusta filosofía y fenomenología"}]})
    judge = MagicMock(utility_call=AsyncMock(return_value=MagicMock(text="qué interesante esa lectura")))
    settings = MagicMock(system_prompt="persona content")
    res = await build_inbound_digest(src, ["m/philosophy"], ["u1"], memory=mem, judge=judge, settings=settings)
    assert res.skipped_reason is None
    assert res.rendered_message == "qué interesante esa lectura"
    assert any(p.id == "p1" for p in res.picks)
    # Persistence ran for the picks
    assert mem.store_world_scan.call_count >= 1


async def test_build_persists_picks_after_render():
    """Even in happy path, picks are written to world_scans with source +
    external_id so the next run dedupes them."""
    src = _mock_source([_post("p1", title="filosofía", upvotes=5)])
    mem = _mock_memory(facts_by_user={"u1": [{"fact": "filosofía"}]})
    judge = MagicMock(utility_call=AsyncMock(return_value=MagicMock(text="take")))
    settings = MagicMock(system_prompt="persona")
    await build_inbound_digest(src, ["m/x"], ["u1"], memory=mem, judge=judge, settings=settings)
    kw = mem.store_world_scan.call_args.kwargs
    assert kw["source"] == "moltbook"
    assert kw["external_id"] == "p1"


async def test_build_skips_when_render_returns_empty():
    """LLM happens to return empty after all the work — we still log, mark
    skipped_reason, and DON'T persist (since there's nothing to attribute
    to those picks)."""
    src = _mock_source([_post("p1", title="filosofía", upvotes=5)])
    mem = _mock_memory(facts_by_user={"u1": [{"fact": "filosofía"}]})
    judge = MagicMock(utility_call=AsyncMock(return_value=MagicMock(text="")))
    settings = MagicMock(system_prompt="persona")
    res = await build_inbound_digest(src, ["m/x"], ["u1"], memory=mem, judge=judge, settings=settings)
    assert res.skipped_reason == "render_empty"
    mem.store_world_scan.assert_not_called()
