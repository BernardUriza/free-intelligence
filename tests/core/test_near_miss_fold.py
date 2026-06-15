"""Tests for the deterministic near-miss fold (PR-3 Tier A, 2026-06-14).

WHAT THIS IS:
  PR-1 (`norm_fact`: lowercase + whitespace) collapsed byte-identical auto
  facts (31,590 -> 2,020 rows in prod). A prod measurement on 2026-06-14 found
  that ~⅓ of the 2,020 SURVIVING facts are still trivial restatements of each
  other — differing only by a comma, an accent, a thousands separator, or a
  trailing period:
      "Su cumpleaños es el 11 de junio; cumple 45 años"
      "Su cumpleaños es el 11 de junio, cumple 45 años"   <- just a comma
      "Necesita panel de ~3,500 pesos"
      "Necesita panel de ~3500 pesos"                     <- thousands sep
  `norm_fact` can't fold these; the Haiku judge could, but the judge is FROZEN
  (CONSOLIDATION_MAX_DESTROY_FRACTION = 0.0) because on 2026-06-03 it buried
  Alex's entire CPTSD history by semantic over-grouping.

THE DESIGN (airtight, word-preserving):
  `norm_fact_strong` removes NO words — only surface noise (case, whitespace,
  accents, punctuation, thousands separators). Every content token (noun, verb,
  number, named entity) survives into the fold key, so two facts can only fold
  if they are word-for-word identical modulo orthography. It is therefore
  provably incapable of merging facts that differ in a number, an owner, or any
  word. Determiner-insertion variants ("una transferencia") are deliberately
  NOT folded — that needs judgment and belongs to Tier B. Under-fold is safe;
  over-fold forgets.

Per the mutator rule (.claude/rules/robustness.md), this destructive mutator
lands with BOTH the positive cases it enables AND the resistance cases it must
survive (numeric drift, decimal-vs-integer, owner drift, entity drift,
determiner-meaning).
"""

from __future__ import annotations

from personas.insult.core.near_miss_fold import build_near_miss_plan, norm_fact_strong

# --------------------------------------------------------------------------
# norm_fact_strong — POSITIVE: pure orthographic variants fold
# --------------------------------------------------------------------------


def test_strong_norm_folds_trailing_punctuation():
    assert norm_fact_strong("Comió un cheesecake delicioso.") == norm_fact_strong("Comió un cheesecake delicioso")


def test_strong_norm_folds_internal_punctuation():
    assert norm_fact_strong("cumple 45 años, qué bien") == norm_fact_strong("cumple 45 años qué bien")


def test_strong_norm_folds_accent_difference():
    assert norm_fact_strong("usa modismos como ¿Qué pedo?") == norm_fact_strong("usa modismos como ¿Que pedo?")


def test_strong_norm_folds_case_and_whitespace():
    assert norm_fact_strong("Tiene  un   PERRO") == norm_fact_strong("tiene un perro")


def test_strong_norm_folds_thousands_separator():
    assert norm_fact_strong("Necesita panel de ~3,500 pesos") == norm_fact_strong("Necesita panel de ~3500 pesos")


def test_strong_norm_folds_thousands_separator_dotted():
    """Spanish-style thousands separator '.' folds the same as ','."""
    assert norm_fact_strong("cobró 3.500 pesos") == norm_fact_strong("cobró 3500 pesos")


# --------------------------------------------------------------------------
# norm_fact_strong — RESISTANCE: distinct meaning must NOT share a key
# --------------------------------------------------------------------------


def test_strong_norm_resistance_distinct_number():
    assert norm_fact_strong("Bern le prestó 3500 pesos") != norm_fact_strong("Bern le prestó 5000 pesos")


def test_strong_norm_resistance_distinct_age():
    assert norm_fact_strong("cumple 45 años") != norm_fact_strong("cumple 46 años")


def test_strong_norm_resistance_decimal_not_collapsed_to_integer():
    """The thousands-sep fold must NOT turn a decimal into an integer:
    '3,5 litros' (3.5 L) is NOT '35 litros'."""
    assert norm_fact_strong("toma 3,5 litros") != norm_fact_strong("toma 35 litros")


def test_strong_norm_resistance_distinct_owner():
    """Possessives are content: 'su dinero' (his) != 'mi dinero' (mine).
    The earlier determiner-dropping draft merged these — it must not."""
    assert norm_fact_strong("le devolvió su dinero") != norm_fact_strong("le devolvió mi dinero")


def test_strong_norm_resistance_object_pronoun_preserved():
    """'la mandó a Xalapa' (sent HER) != 'mandó a Xalapa' (sent).
    The object pronoun 'la' is preserved, not dropped as an article."""
    assert norm_fact_strong("Alex la mandó a Xalapa") != norm_fact_strong("Alex mandó a Xalapa")


def test_strong_norm_resistance_distinct_entity():
    assert norm_fact_strong("le hizo un préstamo a Ana") != norm_fact_strong("le hizo un préstamo a Beto")


def test_strong_norm_resistance_inserted_determiner_not_folded():
    """Deliberately conservative: an inserted determiner is NOT an orthographic
    variant. Tier A leaves it for Tier B's judgment rather than risk meaning."""
    assert norm_fact_strong("espera una transferencia") != norm_fact_strong("espera transferencia")


# --------------------------------------------------------------------------
# build_near_miss_plan — produces apply_consolidation_plan-shaped ops
# --------------------------------------------------------------------------


def test_plan_folds_orthographic_variants_keeping_richest_survivor():
    """POSITIVE: two orthographic variants -> survivor NOOP'd, loser DELETE'd.
    Survivor is the longest raw text (richest phrasing)."""
    facts = [
        {"id": 1, "fact": "Tiene un perro"},
        {"id": 2, "fact": "Tiene un perro!!"},
    ]
    plan = build_near_miss_plan(facts)
    by_op = {op["op"]: op for op in plan}
    assert by_op["NOOP"]["id"] == 2
    assert by_op["DELETE"]["id"] == 1


def test_plan_resistance_distinct_facts_untouched():
    """RESISTANCE: facts that differ in a number must NOT be folded — no ops."""
    facts = [
        {"id": 1, "fact": "Bern le prestó 3500 pesos"},
        {"id": 2, "fact": "Bern le prestó 5000 pesos"},
    ]
    assert build_near_miss_plan(facts) == []


def test_plan_resistance_determiner_variants_untouched():
    """RESISTANCE: a determiner difference is left for Tier B, not folded."""
    facts = [
        {"id": 1, "fact": "espera una transferencia"},
        {"id": 2, "fact": "espera transferencia"},
    ]
    assert build_near_miss_plan(facts) == []


def test_plan_singletons_emit_no_ops():
    facts = [
        {"id": 1, "fact": "Le gusta el cine de terror"},
        {"id": 2, "fact": "Vive en Guadalajara"},
        {"id": 3, "fact": "Tiene un perro"},
    ]
    assert build_near_miss_plan(facts) == []


def test_plan_three_way_cluster_keeps_one_survivor():
    facts = [
        {"id": 10, "fact": "Comió un cheesecake delicioso"},
        {"id": 11, "fact": "Comió un cheesecake delicioso."},
        {"id": 12, "fact": "Comió un cheesecake delicioso!!"},
    ]
    plan = build_near_miss_plan(facts)
    noops = [op for op in plan if op["op"] == "NOOP"]
    deletes = [op for op in plan if op["op"] == "DELETE"]
    assert len(noops) == 1
    assert len(deletes) == 2
    touched = {op["id"] for op in plan}
    assert touched == {10, 11, 12}


def test_plan_ops_carry_a_reason():
    facts = [
        {"id": 1, "fact": "Tiene un perro"},
        {"id": 2, "fact": "Tiene un perro."},
    ]
    plan = build_near_miss_plan(facts)
    assert all(op.get("reason") for op in plan)
