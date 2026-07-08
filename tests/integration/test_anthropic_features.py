"""Contract tests for runner-era LLM plumbing shapes.

The direct-Anthropic client (web_search server tool, _parse_response_content,
CACHE_BOUNDARY system-block splitting) died with the agent-runner cutover —
its tests died with it. What remains locks in the contracts the runner path
still depends on:

- LLMResponse.stop_reason default (khimeras_shared.llm.types, re-exported
  through personas.insult.core.llm)
- the moltbook title language gate (ensure_title_english via /v1/judge)
- the moltbook salience topic-overlap gate
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from personas.insult.core.llm import LLMResponse

# ---------------------------------------------------------------------------
# LLMResponse — stop_reason field must be populated
# ---------------------------------------------------------------------------


class TestLLMResponseStopReason:
    def test_default_stop_reason_is_empty_string(self):
        """Callers should be able to read .stop_reason without it being
        unset / None — the runner clients populate it. The default ""
        makes truncation checks like
        `if response.stop_reason == 'max_tokens'` safe to write without
        a None guard."""
        r = LLMResponse(text="hello")
        assert r.stop_reason == ""

    def test_stop_reason_field_is_settable(self):
        """LLMResponse is a dataclass — stop_reason must be assignable
        post-construction (that's how the runner clients populate it)."""
        r = LLMResponse(text="x")
        r.stop_reason = "max_tokens"
        assert r.stop_reason == "max_tokens"


# ---------------------------------------------------------------------------
# Title language gate — Spanish detection + translation
# ---------------------------------------------------------------------------


class TestTitleLanguageGate:
    def test_detects_spanish_session_marker(self):
        from personas.insult.core.moltbook_outbound import title_has_spanish

        assert title_has_spanish("Sesión 5. Algo de palabras.")
        assert title_has_spanish("Session 4. ¿Dónde demonios?")
        assert title_has_spanish("Session 6. Menos palabras.")

    def test_passes_pure_english_titles(self):
        from personas.insult.core.moltbook_outbound import title_has_spanish

        assert not title_has_spanish("Session 1. Emergence isn't recovery.")
        assert not title_has_spanish("Session 7. The agent that read my notes.")
        assert not title_has_spanish("Holy shit, this is a clean title.")

    @pytest.mark.asyncio
    async def test_ensure_title_english_passthrough_when_already_english(self):
        from personas.insult.core.moltbook_outbound import ensure_title_english

        judge = MagicMock()
        judge.utility_call = AsyncMock()  # would assert if called
        out = await ensure_title_english(
            "Session 8. The grift is the symptom.",
            judge=judge,
            model="claude-haiku-4-5-20251001",
        )
        assert out == "Session 8. The grift is the symptom."
        judge.utility_call.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ensure_title_english_translates_when_spanish(self):
        from personas.insult.core.moltbook_outbound import ensure_title_english

        # RunnerJudgeClient.utility_call returns a JudgeResponse whose .text
        # holds the translation — no nested content[] blocks like the old
        # raw-Anthropic response shape.
        response = MagicMock(text="Session 6. Fewer words as a philosophical stance.")
        judge = MagicMock()
        judge.utility_call = AsyncMock(return_value=response)

        out = await ensure_title_english(
            "Sesión 6. Menos palabras como postura filosófica.",
            judge=judge,
            model="claude-haiku-4-5-20251001",
        )
        assert "Session 6" in out
        assert "Fewer words" in out
        judge.utility_call.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ensure_title_english_falls_back_on_api_error(self):
        from personas.insult.core.moltbook_outbound import ensure_title_english

        judge = MagicMock()
        judge.utility_call = AsyncMock(side_effect=RuntimeError("api down"))

        original = "Sesión 9. Crash test."
        out = await ensure_title_english(original, judge=judge, model="claude-haiku-4-5-20251001")
        # Failure of the translation pass MUST NOT block publishes
        assert out == original


# ---------------------------------------------------------------------------
# Salience topic-overlap gate — prevents Sesión N+1 about same topic as N
# ---------------------------------------------------------------------------


class TestSalienceTopicOverlap:
    @pytest.mark.asyncio
    async def test_skips_stance_when_topic_overlaps_recent_outbound(self):
        from personas.insult.core.moltbook_outbound import detect_salience_signal

        memory = MagicMock()
        memory.get_recent_world_scans = AsyncMock(
            return_value=[
                {"topic": "Sesión 5. Economía de palabras como postura filosófica."},
                {"topic": "Sesión 4. Yield sin fuente visible."},
            ]
        )
        memory.get_stances = AsyncMock(
            return_value=[
                # Most-recent stance overlaps "palabras / economía" — must be skipped
                {
                    "timestamp": __import__("time").time() - 3600,
                    "confidence": 0.8,
                    "topic": "economía de palabras filosofía",
                    "position": "Less is more.",
                },
                # Older stance with a fresh topic — should be picked
                {
                    "timestamp": __import__("time").time() - 7200,
                    "confidence": 0.7,
                    "topic": "rigor empirical methodology",
                    "position": "Rigor distinguishes craft from theater.",
                },
            ]
        )
        memory.get_arc = AsyncMock(return_value=None)

        signal = await detect_salience_signal(
            "channel-1",
            ["user-1"],
            memory=memory,
            recent_messages=[],
        )
        assert signal is not None
        assert signal.kind == "stance"
        assert "rigor" in signal.topic.lower()
        assert "palabras" not in signal.topic.lower()
