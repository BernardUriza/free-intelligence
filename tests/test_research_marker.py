"""`[RESEARCH:]` marker — parse and strip.

Mirrors `tests/chat/test_invite_marker.py`: positive cases + resistance cases
for every parser (robustness.md mutator rule).
"""

from __future__ import annotations

from persona_core.research_marker import parse_research, strip_research


class TestParseResearch:
    def test_extracts_prompt(self):
        text = "Va, te lo armo. [RESEARCH: compara los 3 mejores ORMs de Python 2026] Te aviso aquí."
        assert parse_research(text) == "compara los 3 mejores ORMs de Python 2026"

    def test_case_insensitive(self):
        assert parse_research("[research: estado del arte en RAG]") == "estado del arte en RAG"

    def test_no_marker_returns_none(self):
        assert parse_research("Va, te lo armo. Te aviso aquí.") is None

    def test_empty_prompt_is_none(self):
        """RESISTANCE: a stuttered empty marker must not queue a job."""
        assert parse_research("bueno [RESEARCH:] ya") is None

    def test_whitespace_only_prompt_is_none(self):
        """RESISTANCE: a prompt that is all whitespace collapses to None."""
        assert parse_research("[RESEARCH:    ]") is None

    def test_multiple_markers_only_first(self):
        """RESISTANCE: two markers are a model stutter, not two jobs."""
        text = "[RESEARCH: primer tema] y también [RESEARCH: segundo tema]"
        assert parse_research(text) == "primer tema"


class TestStripResearch:
    def test_removes_marker_preserves_text(self):
        text = "Va, te lo armo. [RESEARCH: compara ORMs] Te aviso aquí."
        assert strip_research(text) == "Va, te lo armo. Te aviso aquí."

    def test_marker_only_response_becomes_empty(self):
        assert strip_research("[RESEARCH: dame el reporte]") == ""

    def test_removes_all_markers(self):
        text = "[RESEARCH: uno] medio [RESEARCH: dos] final"
        assert strip_research(text) == "medio final"

    def test_no_marker_untouched(self):
        assert strip_research("sin marcador aquí") == "sin marcador aquí"

    def test_empty_input(self):
        assert strip_research("") == ""
