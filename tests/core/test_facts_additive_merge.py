"""Tests for the ADD-only fact-extraction merge (P0, 2026-06-03).

THE BUG this locks out:
  `extract_user_facts` injected only the semantic top-N subset of a user's
  facts into the extractor's prompt (token economy), but `memory.save_facts`
  REPLACES the entire `source='auto'` snapshot. Saving the extractor's output
  verbatim therefore hard-deleted every auto fact OUTSIDE the top-N — on every
  single turn, with no recovery. A user's auto-facts could never grow past ~10
  ("Alex explains the same thing every day"). The consolidator (every 2 days,
  soft-delete) was the lesser villain; this per-turn hard delete was the real
  one.

THE FIX (`facts.merge_facts_additive` + `get_auto_facts`):
  Union the extractor's output onto the COMPLETE live auto set, so the snapshot
  that `save_facts` writes is always a SUPERSET of what was already stored.
  Extraction can only ADD, never destroy.

Per the mutator rule (.claude/rules/robustness.md), every guard lands with BOTH
the positive case it enables AND the resistance case it must survive.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from personas.insult.cogs.chat.tasks import extract_user_facts
from personas.insult.core.facts import merge_facts_additive

# --------------------------------------------------------------------------
# Pure-function tests for merge_facts_additive (no DB)
# --------------------------------------------------------------------------


def test_merge_adds_genuinely_new_facts():
    """POSITIVE: a fact not already present is appended and reported in `added`."""
    existing = [{"fact": "Le gusta Python", "category": "interests"}]
    incoming = [
        {"fact": "Le gusta Python", "category": "interests"},
        {"fact": "Vive en CDMX", "category": "location"},
    ]
    merged, added = merge_facts_additive(existing, incoming)
    texts = {f["fact"] for f in merged}
    assert texts == {"Le gusta Python", "Vive en CDMX"}
    assert [f["fact"] for f in added] == ["Vive en CDMX"]


def test_merge_preserves_all_existing_when_extractor_returns_subset():
    """RESISTANCE (the bug): the extractor only echoes back a 1-item subset of a
    4-item auto set. NONE of the other three may be dropped — that hard delete
    is exactly what this merge exists to prevent."""
    existing = [
        {"fact": "A — tiene CPTSD", "category": "personal"},
        {"fact": "B — toma quetiapina", "category": "personal"},
        {"fact": "C — casi hospitalizado", "category": "personal"},
        {"fact": "D — usa la técnica STOP", "category": "personal"},
    ]
    # Extractor saw only the top-1 in its prompt and returned just that.
    incoming = [{"fact": "A — tiene CPTSD", "category": "personal"}]
    merged, added = merge_facts_additive(existing, incoming)
    assert {f["fact"] for f in merged} == {f["fact"] for f in existing}
    assert added == [], "nothing new, and crucially nothing lost"


def test_merge_never_shrinks_for_any_extractor_output():
    """RESISTANCE (general): no matter what the extractor returns, the merged
    set is a superset of `existing` and contains every original fact."""
    existing = [{"fact": f"fact-{i}", "category": "general"} for i in range(20)]
    for incoming in ([], [{"fact": "fact-3", "category": "general"}], [{"fact": "brand new", "category": "general"}]):
        merged, _ = merge_facts_additive(existing, incoming)
        assert len(merged) >= len(existing)
        merged_texts = {f["fact"] for f in merged}
        assert all(f["fact"] in merged_texts for f in existing)


def test_merge_dedupes_by_normalized_text():
    """A reworded-only-by-whitespace/case duplicate is NOT appended."""
    existing = [{"fact": "Vive en CDMX", "category": "location"}]
    incoming = [{"fact": "  vive   EN   cdmx ", "category": "location"}]
    merged, added = merge_facts_additive(existing, incoming)
    assert len(merged) == 1
    assert added == []


def test_merge_empty_incoming_is_noop():
    existing = [{"fact": "solo", "category": "general"}]
    merged, added = merge_facts_additive(existing, [])
    assert merged == existing
    assert added == []


def test_merge_skips_blank_incoming_facts():
    existing = [{"fact": "real", "category": "general"}]
    incoming = [{"fact": "", "category": "general"}, {"category": "general"}]
    merged, added = merge_facts_additive(existing, incoming)
    assert merged == existing
    assert added == []


def test_merge_defaults_missing_category_to_general():
    merged, added = merge_facts_additive([], [{"fact": "sin categoría"}])
    assert added == [{"fact": "sin categoría", "category": "general"}]
    assert merged == added


# --------------------------------------------------------------------------
# PR-1 facts dedup (2026-06-11): existing copies are folded, never re-emitted
# --------------------------------------------------------------------------


def test_merge_dedupes_existing_copies():
    """POSITIVE (PR-1): byte-identical-normalized copies in `existing` collapse
    to one row, so the snapshot stops re-inserting them on every save. Prod had
    31,590 live rows over 1,517 distinct facts (20.8x) from exactly this."""
    existing = [
        {"id": 1, "fact": "Tiene un perro rescatado", "category": "personal"},
        {"id": 2, "fact": "Tiene un perro rescatado", "category": "personal"},
        {"id": 3, "fact": "  tiene   UN perro rescatado ", "category": "personal"},
        {"id": 4, "fact": "Vive en GDL", "category": "location"},
    ]
    merged, added = merge_facts_additive(existing, [])
    assert added == []
    assert [f["fact"] for f in merged] == ["Tiene un perro rescatado", "Vive en GDL"]


def test_merge_existing_dedup_keeps_first_occurrence_verbatim():
    """The surviving row is the FIRST occurrence, preserved verbatim (id and
    casing intact) — dedup never rewrites the fact it keeps."""
    existing = [
        {"id": 7, "fact": "Le gusta el CINE de terror", "category": "interests"},
        {"id": 9, "fact": "le gusta el cine de terror", "category": "interests"},
    ]
    merged, _ = merge_facts_additive(existing, [])
    assert merged == [{"id": 7, "fact": "Le gusta el CINE de terror", "category": "interests"}]


def test_merge_double_pass_is_idempotent():
    """IDEMPOTENCE (the gate test): re-running the merge over its own output —
    the same turn re-executed — must not change the fact count."""
    existing = [
        {"fact": "A", "category": "general"},
        {"fact": "A", "category": "general"},
        {"fact": "B", "category": "general"},
    ]
    incoming = [{"fact": "C", "category": "general"}]
    once, _ = merge_facts_additive(existing, incoming)
    twice, added_twice = merge_facts_additive(once, incoming)
    assert twice == once
    assert added_twice == []


def test_merge_distinct_texts_never_collapse():
    """RESISTANCE (PR-1): near-miss rewordings are DISTINCT facts and must all
    survive — only byte-identical-normalized copies fold. Collapsing these is
    the consolidator's job, gated separately."""
    existing = [
        {"fact": "Aprecia a su perro rescatado, mostrando dedicación en su cuidado", "category": "personal"},
        {
            "fact": "Aprecia a su perro rescatado, mostrando dedicación y paciencia en su cuidado",
            "category": "personal",
        },
        {"fact": "Bernard aprecia a su perro rescatado, mostrando dedicación en su cuidado.", "category": "personal"},
    ]
    merged, added = merge_facts_additive(existing, [])
    assert len(merged) == 3, "rewordings are not duplicates; none may be dropped"
    assert added == []


# --------------------------------------------------------------------------
# Flow test: extract_user_facts must save the SUPERSET, never the subset
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_user_facts_saves_superset_not_subset():
    """End-to-end (mocked) proof that the per-turn hard delete is gone.

    `get_auto_facts` returns the FULL 4-fact auto set; the extractor (given the
    top-2 subset) returns only those 2 + 1 new. `save_facts` must receive all 4
    originals + the 1 new = 5, NOT the 3 the extractor emitted."""
    full_auto = [
        {"id": 1, "fact": "A", "category": "personal", "updated_at": 1.0},
        {"id": 2, "fact": "B", "category": "personal", "updated_at": 2.0},
        {"id": 3, "fact": "C", "category": "personal", "updated_at": 3.0},
        {"id": 4, "fact": "D", "category": "personal", "updated_at": 4.0},
    ]
    injected_subset = [{"fact": "A", "category": "personal"}, {"fact": "B", "category": "personal"}]

    memory = MagicMock()
    memory.get_auto_facts = AsyncMock(return_value=full_auto)
    memory.save_facts = AsyncMock()

    async def fake_extract(_llm, _model, _name, existing_facts, _recent):
        # Extractor only ever sees the injected subset and returns it + 1 new.
        assert existing_facts is injected_subset
        return [*injected_subset, {"fact": "E nuevo", "category": "personal"}]

    await extract_user_facts(
        llm=MagicMock(),
        summary_model="m",
        memory=memory,
        bot=MagicMock(),
        user_id="u1",
        user_name="Bernard",
        existing_facts=injected_subset,
        recent=[{"user_name": "Bernard", "content": "hola"}],
        guild_id=None,  # skip post_facts_to_channel
        extract_facts_fn=fake_extract,
        merge_facts_fn=merge_facts_additive,
    )

    memory.save_facts.assert_awaited_once()
    saved = memory.save_facts.await_args.args[1]
    saved_texts = {f["fact"] for f in saved}
    assert saved_texts == {"A", "B", "C", "D", "E nuevo"}, "must persist superset, not the extractor's 3-item subset"


@pytest.mark.asyncio
async def test_extract_user_facts_skips_save_when_nothing_new():
    """No genuinely-new fact → no save at all (so no needless snapshot churn)."""
    full_auto = [{"id": 1, "fact": "A", "category": "personal", "updated_at": 1.0}]
    memory = MagicMock()
    memory.get_auto_facts = AsyncMock(return_value=full_auto)
    memory.save_facts = AsyncMock()

    async def fake_extract(_llm, _model, _name, _existing, _recent):
        return [{"fact": "A", "category": "personal"}]  # already known

    await extract_user_facts(
        llm=MagicMock(),
        summary_model="m",
        memory=memory,
        bot=MagicMock(),
        user_id="u1",
        user_name="Bernard",
        existing_facts=[{"fact": "A", "category": "personal"}],
        recent=[{"user_name": "Bernard", "content": "x"}],
        guild_id=None,
        extract_facts_fn=fake_extract,
        merge_facts_fn=merge_facts_additive,
    )

    memory.save_facts.assert_not_awaited()
