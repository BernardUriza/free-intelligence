"""Tests for insult.core.quality — post-generation quality validation."""

import pytest

from personas.insult.core.quality import _jaccard_similarity, check_quality

# ---------------------------------------------------------------------------
# Quality checks
# ---------------------------------------------------------------------------


class TestCheckQuality:
    def test_challenge_detected(self):
        """Response with 'pero' + question mark = has_value_move."""
        result = check_quality(
            response="Pero de verdad crees eso? No tiene sentido.",
            user_message="Creo que el cielo es verde.",
            recent_shapes=[],
        )
        assert result.has_value_move is True

    def test_deepening_detected(self):
        """Response adds 5+ new content words = has_value_move."""
        result = check_quality(
            response="La arquitectura neuronal permite inferencias distribuidas sobre grafos complejos mediante transformaciones.",
            user_message="Me gusta la inteligencia artificial.",
            recent_shapes=[],
        )
        assert result.has_value_move is True

    def test_discovery_question(self):
        """Question with new words not in user message = has_value_move."""
        result = check_quality(
            response="Alguna vez consideraste la perspectiva epistemologica?",
            user_message="No estoy seguro de eso.",
            recent_shapes=[],
        )
        assert result.has_value_move is True

    def test_clarification_detected(self):
        """Reframing language ('o sea') = has_value_move."""
        result = check_quality(
            response="O sea, lo que dices no aplica aqui.",
            user_message="Pienso que si funciona.",
            recent_shapes=[],
        )
        assert result.has_value_move is True

    def test_no_value_move(self):
        """Empty/trivial response has no value move."""
        result = check_quality(
            response="ok",
            user_message="Hola como estas?",
            recent_shapes=[],
        )
        assert result.has_value_move is False
        assert any("no_value_move" in v for v in result.violations)

    def test_obvious_paraphrase(self):
        """High Jaccard with few new words = obvious."""
        result = check_quality(
            response="Me gusta mucho programar software cada dia.",
            user_message="Me gusta mucho programar software.",
            recent_shapes=[],
        )
        assert result.is_obvious is True
        assert any("obvious_paraphrase" in v for v in result.violations)

    def test_not_obvious_when_adds_content(self):
        """Even if some overlap, 5+ new words = not obvious."""
        result = check_quality(
            response="Me gusta programar pero ademas considero fundamental explorar arquitecturas distribuidas modernas.",
            user_message="Me gusta programar software.",
            recent_shapes=[],
        )
        assert result.is_obvious is False

    def test_structural_variety_ok(self):
        """Shape not repeated 3x in recent = OK."""
        result = check_quality(
            response="Esto es diferente.",
            user_message="Dime algo.",
            recent_shapes=["question", "statement", "question"],
        )
        assert result.structural_variety_ok is True

    def test_structural_variety_fail(self):
        """Same shape 3+ times in recent = not OK."""
        result = check_quality(
            response="Otra vez lo mismo.",
            user_message="Dime algo.",
            recent_shapes=["question", "question", "question"],
        )
        assert result.structural_variety_ok is False
        assert any("structural_repetition" in v for v in result.violations)

    def test_agreement_streak_violation(self):
        """Streak >= 2 adds a violation."""
        result = check_quality(
            response="Totalmente de acuerdo contigo en todo.",
            user_message="Creo que esto es correcto.",
            recent_shapes=[],
            agreement_streak=3,
        )
        assert any("agreement_streak_high: 3" in v for v in result.violations)

    def test_clean_response(self):
        """A good response passes all checks with no violations."""
        result = check_quality(
            response="Sin embargo, la cuestion fundamental es otra: por que asumes que la correlacion implica causalidad? Eso revela un problema epistemologico interesante.",
            user_message="Los datos muestran que hay una relacion clara.",
            recent_shapes=["statement", "question"],
        )
        assert result.has_value_move is True
        assert result.is_obvious is False
        assert result.structural_variety_ok is True
        assert result.violations == []


# ---------------------------------------------------------------------------
# Jaccard similarity
# ---------------------------------------------------------------------------


class TestJaccardSimilarity:
    def test_jaccard_similarity_empty_sets(self):
        """Empty sets return 0.0."""
        assert _jaccard_similarity(set(), set()) == 0.0
        assert _jaccard_similarity({"a"}, set()) == 0.0
        assert _jaccard_similarity(set(), {"b"}) == 0.0

    def test_jaccard_identical_sets(self):
        """Identical sets return 1.0."""
        assert _jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0

    def test_jaccard_disjoint_sets(self):
        """Disjoint sets return 0.0."""
        assert _jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0

    def test_jaccard_partial_overlap(self):
        """Partial overlap returns correct ratio."""
        # intersection = {b}, union = {a, b, c} → 1/3
        result = _jaccard_similarity({"a", "b"}, {"b", "c"})
        assert result == pytest.approx(1 / 3)
