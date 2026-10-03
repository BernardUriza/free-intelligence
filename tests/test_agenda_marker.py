"""`[AGENDA:]` marker — parse and strip.

Mirrors `tests/test_research_marker.py`: positive cases + resistance cases
for every parser (robustness.md mutator rule).
"""

from __future__ import annotations

from persona_core.agenda_marker import parse_agenda, strip_agenda


class TestParseAgenda:
    def test_extracts_goal(self):
        text = "Va, me quedo pendiente. [AGENDA: vigila novedades sobre difusión estable en video] Te aviso aquí."
        assert parse_agenda(text) == "vigila novedades sobre difusión estable en video"

    def test_case_insensitive(self):
        assert parse_agenda("[agenda: sigue el juicio de X]") == "sigue el juicio de X"

    def test_no_marker_returns_none(self):
        assert parse_agenda("Va, me quedo pendiente. Te aviso aquí.") is None

    def test_empty_goal_is_none(self):
        """RESISTANCE: a stuttered empty marker must not create an agenda."""
        assert parse_agenda("bueno [AGENDA:] ya") is None

    def test_whitespace_only_goal_is_none(self):
        """RESISTANCE: a goal that is all whitespace collapses to None."""
        assert parse_agenda("[AGENDA:    ]") is None

    def test_multiple_markers_only_first(self):
        """RESISTANCE: two markers are a model stutter, not two agendas."""
        text = "[AGENDA: primer tema] y también [AGENDA: segundo tema]"
        assert parse_agenda(text) == "primer tema"


class TestStripAgenda:
    def test_removes_marker_preserves_text(self):
        text = "Va, me quedo pendiente. [AGENDA: vigila X] Te aviso aquí."
        assert strip_agenda(text) == "Va, me quedo pendiente. Te aviso aquí."

    def test_marker_only_response_becomes_empty(self):
        assert strip_agenda("[AGENDA: vigila las noticias de Y]") == ""

    def test_removes_all_markers(self):
        text = "[AGENDA: uno] medio [AGENDA: dos] final"
        assert strip_agenda(text) == "medio final"

    def test_no_marker_untouched(self):
        assert strip_agenda("sin marcador aquí") == "sin marcador aquí"

    def test_empty_input(self):
        assert strip_agenda("") == ""
