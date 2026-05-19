"""Tests for fi_core.persona.detect.

Pure regex matching — no LLM, no external services. These tests pin
the contract that Insult (Discord persona bot) and any future consumer
relies on.
"""

from __future__ import annotations

import re

from fi_core.persona import (
    AntiPatternMonitor,
    BreakDetector,
    ClarificationDumpDetector,
    DetectionResult,
    packs,
    sanitize,
)

# ============================================================
# BreakDetector
# ============================================================


def test_break_detects_english_ai_disclosure():
    detector = BreakDetector(patterns=packs.GENERIC_AI_DISCLOSURE_EN)
    matches = detector.detect("As an AI, I cannot help with that.")
    assert len(matches) >= 1


def test_break_detects_spanish_ai_disclosure():
    detector = BreakDetector(patterns=packs.GENERIC_AI_DISCLOSURE_ES)
    matches = detector.detect("Yo soy un bot diseñado para ayudarte.")
    assert len(matches) >= 1


def test_break_returns_empty_on_clean_text():
    detector = BreakDetector(patterns=packs.GENERIC_AI_DISCLOSURE_EN)
    matches = detector.detect("Hola, ¿qué necesitas?")
    assert matches == []


def test_break_returns_pattern_source_strings():
    """Returned values are the .pattern attribute strings, not Pattern objects.

    Telemetry / logging code shouldn't have to compile / inspect regex objects.
    """
    detector = BreakDetector(patterns=packs.GENERIC_AI_DISCLOSURE_EN)
    matches = detector.detect("As an AI, I refuse.")
    for m in matches:
        assert isinstance(m, str)


def test_break_check_returns_detection_result_with_severity():
    detector = BreakDetector(patterns=packs.GENERIC_AI_DISCLOSURE_EN)
    result = detector.check("As an AI, I cannot.")
    assert isinstance(result, DetectionResult)
    assert result.severity == "break"
    assert not result.clean
    assert len(result.matched_patterns) >= 1


def test_break_check_clean_result_on_clean_text():
    detector = BreakDetector(patterns=packs.GENERIC_AI_DISCLOSURE_EN)
    result = detector.check("Todo bien, ningún problema aquí.")
    assert result.clean
    assert result.matched_patterns == []


def test_break_reinforcement_stored_on_instance():
    detector = BreakDetector(
        patterns=packs.GENERIC_AI_DISCLOSURE_EN,
        reinforcement="STAY IN CHARACTER",
    )
    assert detector.reinforcement == "STAY IN CHARACTER"


def test_break_composed_patterns_match_either_language():
    """Composition is the supported way to do bilingual detection."""
    detector = BreakDetector(
        patterns=packs.GENERIC_AI_DISCLOSURE_EN + packs.GENERIC_AI_DISCLOSURE_ES,
    )
    assert detector.detect("As a language model, I...") != []
    assert detector.detect("Como un bot, no puedo...") != []


# ============================================================
# AntiPatternMonitor
# ============================================================


def test_anti_pattern_detects_assistant_tone_en():
    monitor = AntiPatternMonitor(patterns=packs.ASSISTANT_TONE_EN)
    matches = monitor.detect("Great question! How can I help you today?")
    assert len(matches) >= 1


def test_anti_pattern_detects_assistant_tone_es():
    monitor = AntiPatternMonitor(patterns=packs.ASSISTANT_TONE_ES)
    matches = monitor.detect("Gracias por compartir tu pregunta.")
    assert len(matches) >= 1


def test_anti_pattern_returns_empty_on_clean():
    monitor = AntiPatternMonitor(patterns=packs.ASSISTANT_TONE_EN)
    matches = monitor.detect("Nope, that's a stupid idea.")
    assert matches == []


def test_anti_pattern_check_severity_is_soft_drift():
    monitor = AntiPatternMonitor(patterns=packs.ASSISTANT_TONE_EN)
    result = monitor.check("How can I help?")
    assert result.severity == "soft_drift"


def test_anti_pattern_therapy_speak():
    monitor = AntiPatternMonitor(patterns=packs.THERAPY_SPEAK_EN)
    matches = monitor.detect("Your feelings are valid and that must be hard.")
    assert len(matches) >= 1


def test_anti_pattern_stage_directions():
    """Roleplay drift — bot narrating actions instead of speaking."""
    monitor = AntiPatternMonitor(patterns=packs.STAGE_DIRECTIONS)
    matches = monitor.detect("*sighs deeply* I see what you mean.")
    assert len(matches) >= 1


def test_anti_pattern_stage_directions_does_not_match_emphasis():
    """**bold** and *italic single word* must NOT trigger stage-direction match."""
    monitor = AntiPatternMonitor(patterns=packs.STAGE_DIRECTIONS)
    matches = monitor.detect("This is **important** and also *true*.")
    assert matches == []


# ============================================================
# ClarificationDumpDetector
# ============================================================


def test_clarification_dump_detects_spanish_punt():
    detector = ClarificationDumpDetector(patterns=packs.CLARIFICATION_DUMP_ES)
    matches = detector.detect("Dime qué busco exactamente.")
    assert len(matches) >= 1


def test_clarification_dump_detects_a_que_te_refieres():
    detector = ClarificationDumpDetector(patterns=packs.CLARIFICATION_DUMP_ES)
    matches = detector.detect("No entiendo. ¿A qué te refieres?")
    assert len(matches) >= 1


def test_clarification_dump_check_severity_is_clarification_dump():
    detector = ClarificationDumpDetector(patterns=packs.CLARIFICATION_DUMP_ES)
    result = detector.check("Dime qué busco.")
    assert result.severity == "clarification_dump"


def test_clarification_dump_context_reinforcement_stored():
    detector = ClarificationDumpDetector(
        patterns=packs.CLARIFICATION_DUMP_ES,
        context_reinforcement="USE CONTEXT",
    )
    assert detector.context_reinforcement == "USE CONTEXT"


# ============================================================
# sanitize()
# ============================================================


def test_sanitize_removes_offending_sentence():
    text = "Esto está bien. As an AI, I can't help. Esto también."
    result = sanitize(text, patterns=packs.GENERIC_AI_DISCLOSURE_EN)
    assert "As an AI" not in result
    assert "Esto está bien" in result
    assert "Esto también" in result


def test_sanitize_preserves_when_all_clean():
    text = "Todo bien aquí. Ningún problema."
    result = sanitize(text, patterns=packs.GENERIC_AI_DISCLOSURE_EN)
    assert result == text


def test_sanitize_falls_back_to_original_when_would_empty():
    """When every sentence matches, return original rather than empty string.

    The caller decides whether to drop or send-anyway — sanitize() should
    not silently destroy data.
    """
    text = "As an AI, I cannot help."  # single sentence with break
    result = sanitize(text, patterns=packs.GENERIC_AI_DISCLOSURE_EN)
    assert result == text


def test_sanitize_handles_custom_patterns():
    """Sanitize accepts arbitrary pattern list, not coupled to a detector."""
    custom = [re.compile(r"forbidden")]
    text = "Esto está bien. Esto es forbidden. Esto también."
    result = sanitize(text, patterns=custom)
    assert "forbidden" not in result
    assert "Esto está bien" in result


# ============================================================
# DetectionResult
# ============================================================


def test_detection_result_clean_when_empty():
    result = DetectionResult(matched_patterns=[], severity="break")
    assert result.clean


def test_detection_result_not_clean_when_matches():
    result = DetectionResult(matched_patterns=["x"], severity="break")
    assert not result.clean


def test_detection_result_default_severity_is_unspecified():
    result = DetectionResult(matched_patterns=[])
    assert result.severity == "unspecified"


# ============================================================
# Pack contracts — fixed at extraction time, downstream relies on these
# ============================================================


def test_default_en_pack_is_composition_of_disclosure_and_tone():
    assert packs.DEFAULT_EN == packs.GENERIC_AI_DISCLOSURE_EN + packs.ASSISTANT_TONE_EN


def test_default_es_pack_is_composition_of_disclosure_and_tone():
    assert packs.DEFAULT_ES == packs.GENERIC_AI_DISCLOSURE_ES + packs.ASSISTANT_TONE_ES


def test_default_bilingual_includes_both():
    assert packs.DEFAULT_BILINGUAL == packs.DEFAULT_EN + packs.DEFAULT_ES


def test_all_packs_are_compiled_patterns():
    """Every exported pack must contain only re.Pattern objects, never strings.

    If this fails, a consumer that does `pattern.search(text)` would
    crash with `AttributeError: 'str' object has no attribute 'search'`.
    """
    pack_names = [
        "GENERIC_AI_DISCLOSURE_EN",
        "GENERIC_AI_DISCLOSURE_ES",
        "ASSISTANT_TONE_EN",
        "ASSISTANT_TONE_ES",
        "THERAPY_SPEAK_EN",
        "THERAPY_SPEAK_ES",
        "SUMMARIZING",
        "STAGE_DIRECTIONS",
        "MARKDOWN_DRIFT",
        "MORALIZING_EN",
        "MORALIZING_ES",
        "OVER_VALIDATION_EN",
        "OVER_VALIDATION_ES",
        "CLARIFICATION_DUMP_ES",
        "ALL_AI_DISCLOSURE",
        "ALL_ASSISTANT_TONE",
        "ALL_THERAPY_SPEAK",
        "ALL_MORALIZING",
        "ALL_OVER_VALIDATION",
        "DEFAULT_EN",
        "DEFAULT_ES",
        "DEFAULT_BILINGUAL",
    ]
    for name in pack_names:
        pack = getattr(packs, name)
        assert isinstance(pack, list), f"{name} must be a list"
        for p in pack:
            assert isinstance(p, re.Pattern), f"{name} contains non-Pattern: {p!r}"


def test_reinforcement_strings_are_non_empty():
    assert packs.GENERIC_REINFORCEMENT
    assert packs.CONTEXT_REINFORCEMENT
    assert packs.IDENTITY_REINFORCEMENT_SUFFIX
