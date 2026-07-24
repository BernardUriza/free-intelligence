"""Invariants ride EVERY turn, ahead of everything else.

2026-07-23: asked about concerts, the persona offered Bernard a Christian-rock
band. He is an atheist. Two holes — no fact said so (the extractor was never
told a worldview is worth keeping), and even if one had existed it could not
have arrived: the only automatic fact channel is 8 hits ranked by similarity to
the ask, and nothing about atheism resembles "when does this band play live".

Mutator rule: positive (a `constraint` fact reaches the guidance on a turn whose
topic has NOTHING to do with it) + resistance (tastes are not invariants, the
16k truncation eats prose before invariants, and a store fault degrades to a
normal turn instead of muting it).
"""

from __future__ import annotations

from unittest.mock import patch

from khimeras_shared.constraints import (
    MAX_CONSTRAINTS,
    build_constraints_block,
    select_constraints,
)
from khimeras_shared.guidance import MAX_GUIDANCE_CHARS, build_turn_guidance

ATHEIST = {"fact": "Es ateo", "category": "constraint"}
VEGAN = {"fact": "Es vegano", "category": "constraint"}
TASTE = {"fact": "Le gusta el house de Disciples", "category": "interests"}


def test_selects_only_the_reserved_category():
    picked = select_constraints([ATHEIST, TASTE, VEGAN])
    assert picked == ["Es ateo", "Es vegano"]


def test_category_matching_is_case_and_space_insensitive():
    assert select_constraints([{"fact": "Es ateo", "category": " Constraint "}]) == ["Es ateo"]


def test_block_is_none_without_invariants():
    assert build_constraints_block([TASTE]) is None
    assert build_constraints_block([]) is None
    assert build_constraints_block(None) is None


def test_block_carries_the_facts_and_the_veto_framing():
    block = build_constraints_block([ATHEIST, VEGAN])
    assert "- Es ateo" in block
    assert "- Es vegano" in block
    assert "INVARIANTES" in block


def test_restatements_of_one_invariant_collapse_to_the_richest():
    """The store is ADD-only across personas, so 'es vegano' exists 14 times in
    14 wordings. Undeduped, one restriction eats the whole block."""
    picked = select_constraints(
        [
            {"fact": "Es vegano", "category": "constraint"},
            {"fact": "es vegano.", "category": "constraint"},
            {"fact": "Es vegano absolutista y abolicionista", "category": "constraint"},
            {"fact": "Es ateo", "category": "constraint"},
        ]
    )
    assert picked == ["Es vegano absolutista y abolicionista", "Es ateo"]


def test_constraints_are_capped_but_never_dropped_silently():
    many = [{"fact": f"invariante {i}", "category": "constraint"} for i in range(MAX_CONSTRAINTS + 10)]
    assert len(select_constraints(many)) == MAX_CONSTRAINTS


def test_a_store_fault_degrades_to_no_block_not_a_crash():
    with patch("khimeras_shared.constraints.load_prompt", side_effect=RuntimeError("prompt gone")):
        assert build_constraints_block([ATHEIST]) is None


def test_invariant_reaches_the_guidance_of_an_unrelated_turn():
    """THE regression: a question about concerts must still carry 'es ateo'."""
    guidance = build_turn_guidance(
        current_message="oigan, ¿cuándo toca Disciples en vivo próximamente?",
        recent_messages=[],
        user_facts=[ATHEIST, TASTE],
        persona_id="insult",
    )
    assert guidance is not None
    assert "Es ateo" in guidance


def test_invariants_survive_the_guidance_truncation():
    """RESISTANCE: the 16k cap must eat preset prose, never an invariant — so the
    block goes FIRST."""
    huge = "x" * (MAX_GUIDANCE_CHARS * 2)
    with patch("khimeras_shared.guidance.build_preset_prompt", return_value=huge):
        guidance = build_turn_guidance(
            current_message="hola",
            recent_messages=[],
            user_facts=[ATHEIST],
            persona_id="insult",
        )
    assert len(guidance) == MAX_GUIDANCE_CHARS
    assert "Es ateo" in guidance


def test_a_turn_without_invariants_is_unchanged():
    """RESISTANCE: users with no invariants get exactly the old guidance."""
    with_none = build_turn_guidance(
        current_message="hola",
        recent_messages=[],
        user_facts=[TASTE],
        persona_id="insult",
    )
    assert with_none is not None
    assert "INVARIANTES" not in with_none
