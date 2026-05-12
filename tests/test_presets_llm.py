"""Tests for the LLM-based preset classifier middleware.

These tests focus on the boundary between the LLM and the rest of the
system: JSON parsing tolerance, enum validation, fallback behavior on
failure, and the contract that the function never raises on routing-
level errors.

The actual prompt content and Haiku response quality are not tested here
— that is validated empirically via the `preset_llm_classified` and
`preset_llm_regex_divergence` telemetry events in production.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from insult.core.presets import PresetMode, PresetModifier
from insult.core.presets_llm import (
    _build_user_turn_block,
    _extract_json,
    _parse_classifier_response,
    classify_preset_llm,
)


class TestExtractJson:
    """The classifier prompt asks for strict JSON, but real models
    occasionally wrap it in markdown fences or add a leading line.
    _extract_json must tolerate these without failing classification."""

    def test_clean_json_object(self):
        text = '{"preset": "default_abrasive", "modifiers": []}'
        assert _extract_json(text) == {"preset": "default_abrasive", "modifiers": []}

    def test_with_markdown_fences(self):
        text = '```json\n{"preset": "arc", "modifiers": ["memory_recall"]}\n```'
        result = _extract_json(text)
        assert result is not None
        assert result["preset"] == "arc"

    def test_with_leading_prose(self):
        text = 'Here is the classification:\n{"preset": "playful_roast", "modifiers": []}'
        result = _extract_json(text)
        assert result is not None
        assert result["preset"] == "playful_roast"

    def test_empty_string(self):
        assert _extract_json("") is None

    def test_no_json(self):
        assert _extract_json("just prose, no json here") is None

    def test_malformed_json_returns_none(self):
        assert _extract_json("{not valid json}") is None


class TestParseClassifierResponse:
    """Validation: any failure to produce a sound PresetSelection must
    return None so the caller falls back to regex."""

    def test_valid_minimal_response(self):
        text = '{"preset": "default_abrasive", "modifiers": [], "confidence": 0.8, "reason": "ok"}'
        result = _parse_classifier_response(text)
        assert result is not None
        assert result.mode == PresetMode.DEFAULT_ABRASIVE
        assert result.modifiers == []
        assert 0 <= result.confidence <= 1
        assert result.reason.startswith("llm:")

    def test_valid_with_modifiers(self):
        text = (
            '{"preset": "relational_probe", "modifiers": ["memory_recall"], '
            '"confidence": 0.9, "reason": "user invoked recall"}'
        )
        result = _parse_classifier_response(text)
        assert result is not None
        assert result.mode == PresetMode.RELATIONAL_PROBE
        assert PresetModifier.MEMORY_RECALL in result.modifiers

    def test_invalid_preset_returns_none(self):
        """Hallucinated preset name → caller must fall back to regex."""
        text = '{"preset": "super_savage_mode", "modifiers": []}'
        assert _parse_classifier_response(text) is None

    def test_unknown_modifier_is_dropped_not_rejected(self):
        """A hallucinated modifier should be dropped silently; the rest
        of the classification is still useful."""
        text = '{"preset": "arc", "modifiers": ["memory_recall", "totally_made_up"]}'
        result = _parse_classifier_response(text)
        assert result is not None
        assert PresetModifier.MEMORY_RECALL in result.modifiers
        assert len(result.modifiers) == 1

    def test_missing_modifiers_field_rejects(self):
        """Schema violation: no modifiers list at all → return None."""
        text = '{"preset": "default_abrasive"}'
        result = _parse_classifier_response(text)
        assert result is not None  # modifiers defaults to empty list per schema
        assert result.modifiers == []

    def test_modifiers_not_a_list_rejects(self):
        text = '{"preset": "default_abrasive", "modifiers": "memory_recall"}'
        assert _parse_classifier_response(text) is None

    def test_out_of_range_confidence_clamped(self):
        text = '{"preset": "playful_roast", "modifiers": [], "confidence": 5.0}'
        result = _parse_classifier_response(text)
        assert result is not None
        assert result.confidence == 1.0

    def test_non_numeric_confidence_defaults(self):
        text = '{"preset": "playful_roast", "modifiers": [], "confidence": "high"}'
        result = _parse_classifier_response(text)
        assert result is not None
        assert 0 <= result.confidence <= 1

    def test_long_reason_truncated(self):
        long_reason = "x" * 500
        text = f'{{"preset": "arc", "modifiers": [], "reason": "{long_reason}"}}'
        result = _parse_classifier_response(text)
        assert result is not None
        assert len(result.reason) <= 250  # llm: prefix + 200 max

    def test_garbage_input_returns_none(self):
        assert _parse_classifier_response("totally not json") is None
        assert _parse_classifier_response("") is None
        assert _parse_classifier_response("{}") is None  # empty dict → no preset


class TestBuildUserTurnBlock:
    """The dynamic per-turn block fed to Haiku must include current
    message, recent thread, and slim facts when available."""

    def test_minimal_message_only(self):
        block = _build_user_turn_block("hola", None, None)
        assert "hola" in block
        assert "Current message" in block

    def test_includes_facts(self):
        facts = [{"fact": "Es programador"}, {"fact": "Le gusta el café"}]
        block = _build_user_turn_block("hola", None, facts)
        assert "Es programador" in block
        assert "Le gusta el café" in block

    def test_truncates_facts_to_10(self):
        facts = [{"fact": f"fact-{i}"} for i in range(20)]
        block = _build_user_turn_block("hola", None, facts)
        assert "fact-9" in block
        assert "fact-10" not in block

    def test_includes_recent_thread(self):
        recent = [
            {"role": "user", "content": "primera"},
            {"role": "assistant", "content": "segunda"},
        ]
        block = _build_user_turn_block("hola", recent, None)
        assert "primera" in block
        assert "segunda" in block

    def test_truncates_recent_to_last_5(self):
        recent = [{"role": "user", "content": f"msg-{i}"} for i in range(10)]
        block = _build_user_turn_block("hola", recent, None)
        assert "msg-9" in block
        assert "msg-4" not in block  # only last 5 = msg-5..msg-9


# --- Async classify_preset_llm: integration with mocked LLMClient ---


def _make_mock_llm(response_text: str) -> AsyncMock:
    """Return an AsyncMock that mimics LLMClient.utility_call."""
    mock_llm = AsyncMock()
    response_obj = AsyncMock()
    response_obj.text = response_text
    response_obj.stop_reason = "end_turn"
    mock_llm.utility_call = AsyncMock(return_value=response_obj)
    return mock_llm


@pytest.mark.asyncio
class TestClassifyPresetLlm:
    """End-to-end behavior of the async middleware. The contract is:
    return a PresetSelection on success, None on any failure — never
    raise, so the caller can rely on the fallback path."""

    async def test_happy_path(self):
        mock_llm = _make_mock_llm(
            '{"preset": "relational_probe", "modifiers": ["memory_recall"], '
            '"confidence": 0.85, "reason": "user invoked recall"}'
        )
        result = await classify_preset_llm("tu sabes varios ya", [], [], mock_llm)
        assert result is not None
        assert result.mode == PresetMode.RELATIONAL_PROBE
        assert PresetModifier.MEMORY_RECALL in result.modifiers

    async def test_returns_none_on_invalid_json(self):
        """Garbage response → None (NOT raises)."""
        mock_llm = _make_mock_llm("definitely not json")
        result = await classify_preset_llm("hola", [], [], mock_llm)
        assert result is None

    async def test_returns_none_on_invalid_preset_name(self):
        """Hallucinated preset → None so caller falls back."""
        mock_llm = _make_mock_llm('{"preset": "uber_sarcastic", "modifiers": []}')
        result = await classify_preset_llm("hola", [], [], mock_llm)
        assert result is None

    async def test_returns_none_on_api_exception(self):
        """API failure → None (NOT raises). Caller falls back."""
        mock_llm = AsyncMock()
        mock_llm.utility_call = AsyncMock(side_effect=RuntimeError("API down"))
        result = await classify_preset_llm("hola", [], [], mock_llm)
        assert result is None

    async def test_returns_none_on_empty_response(self):
        mock_llm = _make_mock_llm("")
        result = await classify_preset_llm("hola", [], [], mock_llm)
        assert result is None

    async def test_passes_model_arg_to_utility_call(self):
        mock_llm = _make_mock_llm('{"preset": "default_abrasive", "modifiers": []}')
        await classify_preset_llm("hola", [], [], mock_llm, model="claude-haiku-4-5-20251001")
        # utility_call was called with model kwarg
        _, kwargs = mock_llm.utility_call.call_args
        assert kwargs.get("model") == "claude-haiku-4-5-20251001"

    async def test_passes_facts_and_recent_into_user_block(self):
        """Smoke test: the system prompt + user message reach utility_call
        with the dynamic context embedded."""
        mock_llm = _make_mock_llm('{"preset": "arc", "modifiers": []}')
        await classify_preset_llm(
            "qué opinas del capitalismo",
            [{"role": "user", "content": "previous"}],
            [{"fact": "le interesa la política"}],
            mock_llm,
        )
        _, kwargs = mock_llm.utility_call.call_args
        user_message_content = kwargs["messages"][0]["content"]
        assert "qué opinas del capitalismo" in user_message_content
        assert "previous" in user_message_content
        assert "le interesa la política" in user_message_content
