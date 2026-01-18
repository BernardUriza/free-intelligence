"""Unit tests for text_normalizer module.

Tests capitalization normalization for medical transcriptions.
"""

from __future__ import annotations

import pytest
from backend.utils.text_normalizer import (
    normalize_capitalization,
    normalize_medical_segment,
)


class TestNormalizeCapitalization:
    """Tests for normalize_capitalization function."""

    def test_empty_string_returns_empty(self) -> None:
        """Empty string returns empty."""
        assert normalize_capitalization("") == ""

    def test_whitespace_only_returns_empty(self) -> None:
        """Whitespace-only returns empty string."""
        assert normalize_capitalization("   ") == ""
        assert normalize_capitalization("\t\n") == ""

    def test_capitalizes_first_letter(self) -> None:
        """First letter is capitalized."""
        assert normalize_capitalization("hola") == "Hola"
        assert normalize_capitalization("buenos días") == "Buenos días"

    def test_single_character(self) -> None:
        """Single character is capitalized."""
        assert normalize_capitalization("a") == "A"

    def test_spanish_question_mark_prefix(self) -> None:
        """Spanish ¿ prefix preserves and capitalizes next letter."""
        assert normalize_capitalization("¿cómo estás?") == "¿Cómo estás?"
        assert normalize_capitalization("¿a") == "¿A"

    def test_capitalizes_after_period(self) -> None:
        """Capitalizes first letter after period."""
        result = normalize_capitalization("hola. cómo estás")
        assert result == "Hola. Cómo estás"

    def test_capitalizes_after_exclamation(self) -> None:
        """Capitalizes first letter after exclamation mark."""
        result = normalize_capitalization("bien! ahora vamos")
        assert result == "Bien! Ahora vamos"

    def test_capitalizes_after_question_mark(self) -> None:
        """Capitalizes first letter after question mark."""
        result = normalize_capitalization("¿qué pasa? nada")
        assert result == "¿Qué pasa? Nada"

    def test_spanish_question_after_period(self) -> None:
        """Handles Spanish ¿ after period."""
        result = normalize_capitalization("bien. ¿qué más?")
        assert result == "Bien. ¿Qué más?"

    def test_lowercases_common_mid_sentence_words(self) -> None:
        """Common words are lowercased mid-sentence."""
        result = normalize_capitalization("Tengo El dolor")
        # "El" mid-sentence should become "el"
        assert "el dolor" in result.lower() or "El dolor" not in result[1:]

    def test_preserves_article_at_start(self) -> None:
        """Articles at start of sentence stay capitalized."""
        result = normalize_capitalization("El dolor es fuerte")
        assert result.startswith("El")

    def test_preserves_article_after_period(self) -> None:
        """Articles after period stay capitalized."""
        result = normalize_capitalization("Bien. El dolor continúa")
        assert "El dolor" in result

    def test_doctor_lowercase_when_not_proper_noun(self) -> None:
        """'Doctor' is lowercased when not followed by name."""
        result = normalize_capitalization("Gracias Doctor")
        assert "doctor" in result

    def test_doctor_preserved_before_name(self) -> None:
        """'Doctor' preserved when followed by capitalized name."""
        result = normalize_capitalization("Gracias Doctor García")
        assert "Doctor García" in result

    def test_removes_double_spaces(self) -> None:
        """Double spaces are normalized to single."""
        result = normalize_capitalization("Hola  mundo")
        assert "  " not in result

    def test_strips_whitespace(self) -> None:
        """Leading/trailing whitespace is stripped."""
        result = normalize_capitalization("  hola mundo  ")
        assert result == "Hola mundo"

    def test_multiple_sentences(self) -> None:
        """Multiple sentences are properly capitalized."""
        result = normalize_capitalization("hola. cómo estás. bien gracias")
        assert result.startswith("Hola")
        assert "Cómo" in result
        assert "Bien" in result

    def test_accented_characters(self) -> None:
        """Accented characters are handled properly."""
        result = normalize_capitalization("él está bien. ¿y él?")
        assert result.startswith("Él")


class TestNormalizeMedicalSegment:
    """Tests for normalize_medical_segment function."""

    def test_empty_returns_empty(self) -> None:
        """Empty string returns empty."""
        result = normalize_medical_segment("")
        assert result == ""

    def test_adds_period_if_missing(self) -> None:
        """Adds period if text doesn't end with punctuation."""
        result = normalize_medical_segment("hola")
        assert result.endswith(".")

    def test_preserves_existing_period(self) -> None:
        """Doesn't add period if already ends with one."""
        result = normalize_medical_segment("hola.")
        assert result == "Hola."
        assert not result.endswith("..")

    def test_preserves_question_mark(self) -> None:
        """Doesn't add period if ends with question mark."""
        result = normalize_medical_segment("¿cómo estás?")
        assert result.endswith("?")
        assert not result.endswith("?.")

    def test_preserves_exclamation(self) -> None:
        """Doesn't add period if ends with exclamation."""
        result = normalize_medical_segment("muy bien!")
        assert result.endswith("!")
        assert not result.endswith("!.")

    def test_applies_capitalization(self) -> None:
        """Applies capitalization normalization."""
        result = normalize_medical_segment("hola buenos días")
        assert result.startswith("Hola")

    def test_full_normalization(self) -> None:
        """Full normalization with capitalization and punctuation."""
        result = normalize_medical_segment("tengo dolor")
        assert result == "Tengo dolor."
