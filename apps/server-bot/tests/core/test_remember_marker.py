"""`[REMEMBER:]` marker contract — parse, strip, ADD-only persist.

Mutator rule (.claude/rules/robustness.md): positive case + resistance case. The
load-bearing resistance here is that persistence goes through
`add_remember_fact` (a pure INSERT), NEVER `save_facts` — a snapshot replace of a
subset is the documented hard-delete P0 (memory: facts-extraction-addonly).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from persona_core.remember_marker import (
    MAX_FACTS_PER_TURN,
    parse_remembers,
    persist_remembers,
    strip_remembers,
)

# --------------------------------------------------------------------------
# parse_remembers
# --------------------------------------------------------------------------


def test_parse_extracts_a_single_clause():
    assert parse_remembers("Anotado. [REMEMBER: Alex es entrenadora canina]") == ["Alex es entrenadora canina"]


def test_parse_extracts_two_clauses():
    facts = parse_remembers("[REMEMBER: vive en GDL] ... [REMEMBER: tiene un perro rescatado]")
    assert facts == ["vive en GDL", "tiene un perro rescatado"]


def test_parse_caps_at_max_facts_per_turn():
    """RESISTANCE: a model stuttering five markers may not flood the fact table."""
    text = " ".join(f"[REMEMBER: fact {i}]" for i in range(5))
    assert len(parse_remembers(text)) == MAX_FACTS_PER_TURN


def test_parse_returns_empty_without_marker():
    assert parse_remembers("Una respuesta normal.") == []


def test_parse_skips_empty_clauses():
    assert parse_remembers("[REMEMBER: ]") == []


def test_parse_truncates_an_overlong_clause():
    facts = parse_remembers(f"[REMEMBER: {'y' * 400}]")
    assert len(facts) == 1
    assert len(facts[0]) <= 201
    assert facts[0].endswith("…")


# --------------------------------------------------------------------------
# strip_remembers
# --------------------------------------------------------------------------


def test_strip_removes_marker_and_collapses_hole():
    assert strip_remembers("Ok. [REMEMBER: vive en GDL] Sigue.") == "Ok. Sigue."


def test_strip_without_marker_is_untouched():
    """RESISTANCE: text with no marker survives intact."""
    assert strip_remembers("Respuesta sin marcadores.") == "Respuesta sin marcadores."


def test_strip_empty_is_safe():
    assert strip_remembers("") == ""


# --------------------------------------------------------------------------
# persist_remembers — ADD-only
# --------------------------------------------------------------------------


async def test_persist_uses_add_remember_fact_never_save_facts():
    """THE guard: remembers are appended (source='agent'), never snapshot-saved.

    A `save_facts(subset)` here would DELETE-all-and-reinsert the auto snapshot —
    the exact hard-delete P0 this path must never re-arm."""
    memory = MagicMock()
    memory.add_remember_fact = AsyncMock(return_value=1)
    memory.save_facts = AsyncMock()

    saved = await persist_remembers(memory, "U1", ["vive en GDL", "tiene un perro"])

    assert saved == 2
    assert memory.add_remember_fact.await_count == 2
    memory.save_facts.assert_not_awaited()


async def test_persist_empty_list_is_a_noop():
    memory = MagicMock()
    memory.add_remember_fact = AsyncMock()
    assert await persist_remembers(memory, "U1", []) == 0
    memory.add_remember_fact.assert_not_awaited()


async def test_persist_survives_a_failing_fact_and_saves_the_rest():
    """RESISTANCE: one bad row never raises into the turn nor eats its siblings."""
    memory = MagicMock()
    memory.add_remember_fact = AsyncMock(side_effect=[RuntimeError("pg down"), 2])

    saved = await persist_remembers(memory, "U1", ["falla", "sobrevive"])

    assert saved == 1
    assert memory.add_remember_fact.await_count == 2
