"""Tests for text normalization utilities."""

from __future__ import annotations

from backend.utils.text_normalizer import (
    normalize_capitalization,
    normalize_medical_segment,
)


class TestNormalizeCapitalization:
    """Test capitalize normalization function."""

    def test_capitalize_first_word(self):
        """First word should be capitalized."""
        assert normalize_capitalization("hola buenos días") == "Hola buenos días"
        assert normalize_capitalization("el paciente") == "El paciente"

    def test_capitalize_after_period(self):
        """Capitalize after sentence endings."""
        text = "el dolor es fuerte. la garganta está roja"
        expected = "El dolor es fuerte. La garganta está roja"
        assert normalize_capitalization(text) == expected

    def test_capitalize_after_question_mark(self):
        """Capitalize after question marks."""
        text = "¿cómo está? bien gracias"
        expected = "¿Cómo está? Bien gracias"
        assert normalize_capitalization(text) == expected

    def test_lowercase_common_words(self):
        """Common words should be lowercase mid-sentence."""
        assert normalize_capitalization("el dolor Es muy fuerte") == "El dolor es muy fuerte"
        assert normalize_capitalization("tiene La garganta roja") == "Tiene la garganta roja"
        assert normalize_capitalization("voy Con El doctor") == "Voy con el doctor"

    def test_lowercase_doctor_not_proper_noun(self):
        """'Doctor' should be lowercase when not a proper noun."""
        assert normalize_capitalization("gracias Doctor") == "Gracias doctor"
        assert normalize_capitalization("muy bien Doctor") == "Muy bien doctor"

    def test_preserve_doctor_proper_noun(self):
        """'Doctor' should be preserved when followed by proper noun."""
        text = "veo al Doctor García mañana"
        # This should preserve "Doctor García" as a proper noun
        assert "García" in normalize_capitalization(text)

    def test_empty_string(self):
        """Empty strings should be handled gracefully."""
        assert normalize_capitalization("") == ""
        assert normalize_capitalization("   ") == ""

    def test_single_character(self):
        """Single characters should be capitalized."""
        assert normalize_capitalization("a") == "A"

    def test_real_medical_examples(self):
        """Test with real medical transcription examples."""
        # Example 1: "más que nada al tragar" → "Más que nada al tragar"
        assert normalize_capitalization("más que nada al tragar") == "Más que nada al tragar"

        # Example 2: Multiple sentences
        text = "hola buenas tardes. ¿cómo está? muy bien Doctor"
        expected = "Hola buenas tardes. ¿Cómo está? Muy bien doctor"
        assert normalize_capitalization(text) == expected

        # Example 3: Mid-sentence capitalization errors
        text = "Muchas gracias doctor Espero que disfrute El maravilloso atardecer"
        expected = "Muchas gracias doctor espero que disfrute el maravilloso atardecer"
        assert normalize_capitalization(text) == expected


class TestNormalizeMedicalSegment:
    """Test medical segment normalization."""

    def test_adds_period_if_missing(self):
        """Segment should end with punctuation."""
        result = normalize_medical_segment("hola buenos días")
        assert result.endswith(".")
        assert result == "Hola buenos días."

    def test_preserves_existing_punctuation(self):
        """Existing punctuation should be preserved."""
        result = normalize_medical_segment("¿cómo está?")
        assert result == "¿Cómo está?"
        assert not result.endswith(".")  # Should not add extra period

    def test_full_normalization(self):
        """Full normalization pipeline."""
        text = "más que nada al tragar"
        result = normalize_medical_segment(text)
        assert result == "Más que nada al tragar."

        text = "ya veo la garganta está roja"
        result = normalize_medical_segment(text)
        assert result.startswith("Ya veo")
        assert result.endswith(".")
