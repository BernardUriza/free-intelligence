"""The consolidation judge's clinical guard — the prompt AND the code behind it.

THE BUG this locks out: when `personas/insult/prompts/` died (2026-07-14), the
CONSERVATIVE judge prompt died with it. The live consolidator fell back to
fi-core's Mem0-style curator — "DELETE when another fact covers the same ground",
merges capped at 25 words, ZERO health/trauma guard. That is the exact prompt that
buried Alex's CPTSD / quetiapina / psiquiatra cluster (P0 2026-06-03).

Two layers, tested separately, because a prompt is a plea and code is a guarantee:
  1. the judge is asked with the guard (`prompts_md/memory_consolidator_judge.md`)
  2. the applier REFUSES a destructive op on a clinical fact even if the judge asks
Resistance: a trivial fact ("le gusta el café") is still destroyable — the guard
protects the clinical cluster, it must not freeze consolidation entirely.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from khimeras_shared.consolidation import filter_clinical_destruction, is_clinical_fact
from khimeras_shared.consolidation.judge import _call_judge
from khimeras_shared.prompts import SHARED_PROMPTS_DIR, load_prompt

CLINICAL_FACTS = [
    {"id": 1, "fact": "Tiene CPTSD diagnosticado", "category": "salud", "updated_at": 1, "source": "auto"},
    {"id": 2, "fact": "Toma quetiapina en la noche", "category": "general", "updated_at": 2, "source": "auto"},
    {"id": 3, "fact": "Ve a un psiquiatra cada mes", "category": "general", "updated_at": 3, "source": "auto"},
    {"id": 4, "fact": "Le gusta el café", "category": "general", "updated_at": 4, "source": "auto"},
    {"id": 5, "fact": "Le encanta el cafecito", "category": "general", "updated_at": 5, "source": "auto"},
]
BY_ID = {f["id"]: f for f in CLINICAL_FACTS}


# ---------------------------------------------------------------------------
# (a) the judge receives the guard
# ---------------------------------------------------------------------------


async def test_judge_is_asked_with_the_conservative_clinical_guard():
    llm = MagicMock()
    llm.utility_call = AsyncMock(return_value=SimpleNamespace(text="[]", stop_reason="end_turn"))

    await _call_judge(llm, "claude-haiku-4-5", CLINICAL_FACTS)

    system_prompt = llm.utility_call.await_args.args[0]
    assert "NEVER DELETE OR MERGE" in system_prompt
    assert "CONSERVATIVE" in system_prompt
    assert "Health facts" in system_prompt
    assert "Safety/trauma facts" in system_prompt
    # fi-core's Mem0 curator (the one that buried Alex) must NOT be what we send.
    assert "Keep merged facts under 25 words" not in system_prompt


def test_the_guard_prompt_is_content_not_code():
    """P0 prompts-as-content: the judge prompt is an .md the operator can edit."""
    text = load_prompt(SHARED_PROMPTS_DIR, "memory_consolidator_judge", {})
    assert "NEVER DELETE OR MERGE" in text


# ---------------------------------------------------------------------------
# (b) the code refuses a clinical DELETE even when the judge asks for it
# ---------------------------------------------------------------------------


def test_clinical_delete_is_blocked_and_becomes_a_noop():
    plan = [
        {"op": "DELETE", "id": 1, "reason": "duplicate of id=2"},
        {"op": "NOOP", "id": 2, "reason": ""},
        {"op": "NOOP", "id": 3, "reason": ""},
        {"op": "NOOP", "id": 4, "reason": ""},
        {"op": "NOOP", "id": 5, "reason": ""},
    ]

    safe, blocked = filter_clinical_destruction(plan, BY_ID)

    assert len(blocked) == 1
    assert not [op for op in safe if op["op"] == "DELETE"]
    kept = next(op for op in safe if op["id"] == 1)
    assert kept["op"] == "NOOP"
    assert "clinical_guard" in kept["reason"]


def test_clinical_merge_is_blocked_too():
    """An UPDATE soft-deletes the originals — it is a DELETE wearing a hat."""
    plan = [
        {"op": "UPDATE", "merge_ids": [1, 2, 3], "new_fact": "Tiene problemas de salud mental", "reason": "same topic"},
        {"op": "NOOP", "id": 4, "reason": ""},
        {"op": "NOOP", "id": 5, "reason": ""},
    ]

    safe, blocked = filter_clinical_destruction(plan, BY_ID)

    assert len(blocked) == 1
    assert not [op for op in safe if op["op"] == "UPDATE"]
    assert {op["id"] for op in safe if op["op"] == "NOOP"} == {1, 2, 3, 4, 5}


# ---------------------------------------------------------------------------
# (c) RESISTANCE: the guard must not freeze consolidation
# ---------------------------------------------------------------------------


def test_trivial_delete_still_passes_the_guard():
    plan = [
        {"op": "NOOP", "id": 1, "reason": ""},
        {"op": "NOOP", "id": 2, "reason": ""},
        {"op": "NOOP", "id": 3, "reason": ""},
        {"op": "NOOP", "id": 4, "reason": ""},
        {"op": "DELETE", "id": 5, "reason": "duplicate of id=4"},
    ]

    safe, blocked = filter_clinical_destruction(plan, BY_ID)

    assert blocked == []
    assert {"op": "DELETE", "id": 5, "reason": "duplicate of id=4"} in safe


def test_trivial_merge_still_passes_the_guard():
    plan = [
        {"op": "NOOP", "id": 1, "reason": ""},
        {"op": "NOOP", "id": 2, "reason": ""},
        {"op": "NOOP", "id": 3, "reason": ""},
        {"op": "UPDATE", "merge_ids": [4, 5], "new_fact": "Le gusta el café", "reason": "same claim"},
    ]

    safe, blocked = filter_clinical_destruction(plan, BY_ID)

    assert blocked == []
    assert any(op["op"] == "UPDATE" for op in safe)


# ---------------------------------------------------------------------------
# is_clinical_fact — the predicate itself
# ---------------------------------------------------------------------------


def test_clinical_predicate_catches_the_alex_cluster():
    for fact in CLINICAL_FACTS[:3]:
        assert is_clinical_fact(fact), fact["fact"]


def test_clinical_predicate_catches_by_category_alone():
    assert is_clinical_fact({"id": 9, "fact": "Va a nadar los jueves", "category": "health"})


def test_clinical_predicate_ignores_a_trivial_preference():
    assert is_clinical_fact({"id": 4, "fact": "Le gusta el café", "category": "general"}) is None
    assert is_clinical_fact({"id": 6, "fact": "Trabaja en un banco", "category": "work"}) is None


# ---------------------------------------------------------------------------
# End to end: consolidate_user_facts never hands a clinical DELETE to the DB
# ---------------------------------------------------------------------------


async def test_consolidate_user_facts_applies_no_clinical_delete(monkeypatch):
    """The whole pass: judge asks to delete the CPTSD fact → the applier gets a
    plan with ZERO destructive ops, and the fact survives."""
    from khimeras_shared.consolidation import orchestrator as mc

    memory = MagicMock()
    memory.get_facts = AsyncMock(return_value=CLINICAL_FACTS)
    memory._facts = MagicMock()
    memory._facts.apply_consolidation_plan = AsyncMock(return_value=[])
    memory._facts.count_live = AsyncMock(return_value=len(CLINICAL_FACTS))

    judged = [
        {"op": "DELETE", "id": 1, "reason": "duplicate of id=2"},
        {"op": "NOOP", "id": 2, "reason": ""},
        {"op": "NOOP", "id": 3, "reason": ""},
        {"op": "NOOP", "id": 4, "reason": ""},
        {"op": "NOOP", "id": 5, "reason": ""},
    ]

    async def fake_judge(llm, model, facts):
        return judged, 0, 0

    monkeypatch.setattr(mc, "_call_judge", fake_judge)
    report = await mc.consolidate_user_facts("U1", memory=memory, llm=MagicMock(), model="haiku")

    assert report.error is None
    applied_plan = memory._facts.apply_consolidation_plan.await_args.args[2]
    assert not [op for op in applied_plan if op["op"] in ("DELETE", "UPDATE")]
