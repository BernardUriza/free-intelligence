"""Tests for the ADD-only fact-extraction merge (P0, 2026-06-03).

THE BUG this locks out:
  The extractor only ever SEES a subset of a user's stored facts (the prompt's
  top-N), but `memory.save_facts` REPLACES the entire `source='auto'` snapshot.
  Saving the extractor's output verbatim therefore hard-deleted every auto fact
  OUTSIDE that subset — on every single turn, with no recovery. A user's
  auto-facts could never grow past ~10 ("Alex explains the same thing every day").

THE FIX (`persona_core.facts.merge_facts_additive` + `get_auto_facts`):
  Union the extractor's output onto the COMPLETE live auto set, so the snapshot
  `save_facts` writes is always a SUPERSET of what was already stored. Extraction
  can only ADD, never destroy.

Per the mutator rule (.claude/rules/robustness.md), every guard lands with BOTH
the positive case it enables AND the resistance case it must survive.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from persona_core.facts import build_facts_prompt, extract_facts, merge_facts_additive, norm_fact

# --------------------------------------------------------------------------
# merge_facts_additive — pure
# --------------------------------------------------------------------------


def test_merge_adds_genuinely_new_facts():
    """POSITIVE: a fact not already present is appended and reported in `added`."""
    existing = [{"fact": "Le gusta Python", "category": "interests"}]
    incoming = [
        {"fact": "Le gusta Python", "category": "interests"},
        {"fact": "Vive en CDMX", "category": "location"},
    ]
    merged, added = merge_facts_additive(existing, incoming)
    assert {f["fact"] for f in merged} == {"Le gusta Python", "Vive en CDMX"}
    assert [f["fact"] for f in added] == ["Vive en CDMX"]


def test_merge_preserves_all_existing_when_extractor_returns_subset():
    """RESISTANCE (the bug): the extractor only echoes back a 1-item subset of a
    4-item auto set. NONE of the other three may be dropped — that hard delete is
    exactly what this merge exists to prevent."""
    existing = [
        {"fact": "A — tiene CPTSD", "category": "personal"},
        {"fact": "B — toma quetiapina", "category": "personal"},
        {"fact": "C — casi hospitalizado", "category": "personal"},
        {"fact": "D — usa la técnica STOP", "category": "personal"},
    ]
    incoming = [{"fact": "A — tiene CPTSD", "category": "personal"}]
    merged, added = merge_facts_additive(existing, incoming)
    assert {f["fact"] for f in merged} == {f["fact"] for f in existing}
    assert added == [], "nothing new, and crucially nothing lost"


def test_merge_never_shrinks_for_any_extractor_output():
    """RESISTANCE (general): whatever the extractor returns, the merged set is a
    superset of `existing` and contains every original fact."""
    existing = [{"fact": f"fact-{i}", "category": "general"} for i in range(20)]
    for incoming in ([], [{"fact": "fact-3", "category": "general"}], [{"fact": "brand new", "category": "general"}]):
        merged, _ = merge_facts_additive(existing, incoming)
        assert len(merged) >= len(existing)
        merged_texts = {f["fact"] for f in merged}
        assert all(f["fact"] in merged_texts for f in existing)


def test_merge_dedupes_by_normalized_text():
    """A reworded-only-by-whitespace/case duplicate is NOT appended."""
    merged, added = merge_facts_additive(
        [{"fact": "Vive en CDMX", "category": "location"}],
        [{"fact": "  vive   EN   cdmx ", "category": "location"}],
    )
    assert len(merged) == 1
    assert added == []


def test_merge_empty_incoming_is_noop():
    existing = [{"fact": "solo", "category": "general"}]
    merged, added = merge_facts_additive(existing, [])
    assert merged == existing
    assert added == []


def test_merge_skips_blank_incoming_facts():
    existing = [{"fact": "real", "category": "general"}]
    merged, added = merge_facts_additive(existing, [{"fact": "", "category": "general"}, {"category": "general"}])
    assert merged == existing
    assert added == []


def test_merge_defaults_missing_category_to_general():
    merged, added = merge_facts_additive([], [{"fact": "sin categoría"}])
    assert added == [{"fact": "sin categoría", "category": "general"}]
    assert merged == added


def test_merge_dedupes_existing_copies():
    """POSITIVE (PR-1): byte-identical-normalized copies in `existing` collapse to
    one row, so the snapshot stops re-inserting them on every save. Prod had
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
    merged, _ = merge_facts_additive(
        [
            {"id": 7, "fact": "Le gusta el CINE de terror", "category": "interests"},
            {"id": 9, "fact": "le gusta el cine de terror", "category": "interests"},
        ],
        [],
    )
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
    survive — only byte-identical-normalized copies fold. Collapsing these is the
    consolidator's job, gated separately."""
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


def test_norm_fact_collapses_case_and_whitespace():
    assert norm_fact("  Vive   EN  CDMX ") == "vive en cdmx"


# --------------------------------------------------------------------------
# extract_facts — the judge round-trip
# --------------------------------------------------------------------------


def _judge(text: str, stop_reason: str = "end_turn"):
    llm = MagicMock()
    llm.utility_call = AsyncMock(return_value=SimpleNamespace(text=text, stop_reason=stop_reason))
    return llm


async def test_extract_parses_the_judge_json():
    llm = _judge('[{"fact": "Vive en GDL", "category": "location"}]')
    facts = await extract_facts(llm, None, "Bernard", [], [{"user_name": "Bernard", "content": "vivo en GDL"}])
    assert facts == [{"fact": "Vive en GDL", "category": "location"}]


async def test_extract_unwraps_a_markdown_code_fence():
    llm = _judge('```json\n[{"fact": "Le gusta Rust", "category": "technical"}]\n```')
    facts = await extract_facts(llm, None, "Bernard", [], [{"user_name": "Bernard", "content": "amo rust"}])
    assert facts == [{"fact": "Le gusta Rust", "category": "technical"}]


async def test_extract_returns_existing_on_bad_json():
    """RESISTANCE: garbage from the judge must NEVER erase what is stored."""
    existing = [{"fact": "ya guardado", "category": "general"}]
    llm = _judge("lo siento, no puedo")
    assert await extract_facts(llm, None, "Bernard", existing, [{"user_name": "B", "content": "x"}]) == existing


async def test_extract_returns_existing_on_truncation():
    """RESISTANCE: a max_tokens cut-off yields a partial list — discard it."""
    existing = [{"fact": "ya guardado", "category": "general"}]
    llm = _judge('[{"fact": "a medias"', stop_reason="max_tokens")
    assert await extract_facts(llm, None, "Bernard", existing, [{"user_name": "B", "content": "x"}]) == existing


async def test_extract_returns_existing_when_the_judge_is_down():
    """RESISTANCE: a dead /v1/judge degrades to 'no new facts', never to a wipe."""
    import httpx

    existing = [{"fact": "ya guardado", "category": "general"}]
    llm = MagicMock()
    llm.utility_call = AsyncMock(side_effect=httpx.ConnectError("runner down"))
    assert await extract_facts(llm, None, "Bernard", existing, [{"user_name": "B", "content": "x"}]) == existing


async def test_extract_returns_existing_when_json_is_not_a_list():
    existing = [{"fact": "ya guardado", "category": "general"}]
    llm = _judge('{"fact": "un objeto, no una lista"}')
    assert await extract_facts(llm, None, "Bernard", existing, [{"user_name": "B", "content": "x"}]) == existing


async def test_extract_skips_malformed_rows_and_defaults_category():
    llm = _judge('[{"fact": "ok"}, {"categoria": "sin fact"}, "un string suelto"]')
    facts = await extract_facts(llm, None, "Bernard", [], [{"user_name": "B", "content": "x"}])
    assert facts == [{"fact": "ok", "category": "general"}]


async def test_extract_sends_the_engine_prompt_as_system():
    """The prompt is CONTENT loaded from prompts_md/facts_extraction.md — never an
    inline Python string (playbook: prompts-as-content-not-code)."""
    llm = _judge("[]")
    await extract_facts(llm, None, "Bernard", [], [{"user_name": "B", "content": "hola"}])
    system_prompt = llm.utility_call.await_args.args[0]
    assert "fact extractor" in system_prompt
    assert "JSON array" in system_prompt


# --------------------------------------------------------------------------
# build_facts_prompt
# --------------------------------------------------------------------------


def test_build_facts_prompt_renders_the_lines():
    out = build_facts_prompt("Bernard", [{"fact": "Vive en GDL", "category": "location"}])
    assert "Bernard" in out
    assert "- [location] Vive en GDL" in out


def test_build_facts_prompt_is_empty_without_facts():
    assert build_facts_prompt("Bernard", []) == ""
