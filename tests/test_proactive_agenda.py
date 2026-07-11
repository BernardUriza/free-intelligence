"""`frame_agenda_prompt` / `is_nothing_new` — the autonomy-trigger brain.

Both are pure functions, so the should-it-speak decision is testable without a
live runner or DB.
"""

from __future__ import annotations

from khimeras_shared.proactive_agenda import frame_agenda_prompt, is_nothing_new


class TestFrameAgendaPrompt:
    def test_includes_goal(self):
        prompt = frame_agenda_prompt("vigila novedades sobre RAG")
        assert "vigila novedades sobre RAG" in prompt

    def test_includes_nothing_new_instruction(self):
        prompt = frame_agenda_prompt("cualquier meta")
        assert "NADA" in prompt

    def test_instructs_web_search(self):
        prompt = frame_agenda_prompt("cualquier meta")
        assert "WebSearch" in prompt

    def test_last_result_anchors_since_last_time(self):
        prompt = frame_agenda_prompt("vigila X", last_result="salió el paper Y ayer")
        assert "salió el paper Y ayer" in prompt

    def test_no_last_result_omits_repeat_clause(self):
        prompt = frame_agenda_prompt("vigila X")
        assert "NO lo repitas" not in prompt


class TestIsNothingNew:
    def test_exact_nada_is_nothing(self):
        assert is_nothing_new("NADA") is True

    def test_nada_with_punctuation_is_nothing(self):
        assert is_nothing_new("nada.") is True

    def test_empty_is_nothing(self):
        assert is_nothing_new("") is True

    def test_whitespace_is_nothing(self):
        assert is_nothing_new("   \n\t ") is True

    def test_quoted_nada_is_nothing(self):
        assert is_nothing_new('"nada"') is True

    def test_real_content_is_something(self):
        assert is_nothing_new("Salió un paper nuevo sobre difusión latente...") is False

    def test_nada_inside_sentence_is_something(self):
        assert is_nothing_new("No hay nada que no sepas ya, pero salió esto nuevo") is False
