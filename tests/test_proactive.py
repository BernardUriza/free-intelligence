"""Tests for proactive messaging — activity state, backoff, mood detection."""

import time

import pytest

from insult.core.proactive import (
    ConversationState,
    _detect_conversation_mood,
    _elapsed_description,
    _extract_conversation_topics,
    _extract_participants,
    _pick_search_topic,
    compute_backoff_interval,
    generate_proactive_message,
    get_conversation_state,
    should_send_now,
)

# ---------------------------------------------------------------------------
# Conversation state detection
# ---------------------------------------------------------------------------


class TestConversationState:
    def test_none_timestamp_returns_idle(self):
        assert get_conversation_state(None) == ConversationState.IDLE

    def test_recent_message_returns_active(self):
        # 5 minutes ago = ACTIVE
        ts = time.time() - 5 * 60
        assert get_conversation_state(ts) == ConversationState.ACTIVE

    def test_15_min_boundary_returns_cooling(self):
        # 20 minutes ago = COOLING_DOWN
        ts = time.time() - 20 * 60
        assert get_conversation_state(ts) == ConversationState.COOLING_DOWN

    def test_old_message_returns_idle(self):
        # 3 hours ago = IDLE
        ts = time.time() - 3 * 3600
        assert get_conversation_state(ts) == ConversationState.IDLE

    def test_exactly_at_active_threshold(self):
        # Just past 15 min = COOLING_DOWN
        ts = time.time() - 15 * 60 - 1
        assert get_conversation_state(ts) == ConversationState.COOLING_DOWN

    def test_exactly_at_cooling_threshold(self):
        # Just past 2 hours = IDLE
        ts = time.time() - 2 * 3600 - 1
        assert get_conversation_state(ts) == ConversationState.IDLE


# ---------------------------------------------------------------------------
# Exponential backoff
# ---------------------------------------------------------------------------


class TestBackoff:
    def test_zero_unanswered_returns_base(self):
        assert compute_backoff_interval(0) == 2.0

    def test_one_unanswered_doubles(self):
        assert compute_backoff_interval(1) == 4.0

    def test_two_unanswered_quadruples(self):
        assert compute_backoff_interval(2) == 8.0

    def test_caps_at_max(self):
        assert compute_backoff_interval(10) == 24.0

    def test_three_unanswered(self):
        assert compute_backoff_interval(3) == 16.0


# ---------------------------------------------------------------------------
# should_send_now
# ---------------------------------------------------------------------------


class TestShouldSendNow:
    def test_quiet_hours_blocked(self):
        for hour in (3, 4, 5, 6):
            assert should_send_now(hour, None, None) is False

    def test_active_conversation_blocked(self):
        # User message 5 min ago = ACTIVE, should never send
        recent_ts = time.time() - 5 * 60
        # Run 100 times — should always be False (not probabilistic)
        results = [should_send_now(14, None, recent_ts) for _ in range(100)]
        assert all(r is False for r in results)

    def test_cooling_down_blocked(self):
        # User message 30 min ago = COOLING_DOWN
        recent_ts = time.time() - 30 * 60
        results = [should_send_now(14, None, recent_ts) for _ in range(100)]
        assert all(r is False for r in results)

    def test_idle_allows_sending(self):
        # User message 3 hours ago = IDLE, last proactive 3 hours ago
        user_ts = time.time() - 3 * 3600
        proactive_ts = time.time() - 3 * 3600
        # With 40% probability, some should be True in 100 tries
        results = [should_send_now(14, proactive_ts, user_ts) for _ in range(100)]
        assert any(r is True for r in results)

    def test_backoff_respects_interval(self):
        # 2 unanswered = 8h interval required. Last proactive 3h ago = blocked
        user_ts = time.time() - 10 * 3600  # IDLE
        proactive_ts = time.time() - 3 * 3600  # 3h ago
        results = [should_send_now(14, proactive_ts, user_ts, unanswered_count=2) for _ in range(100)]
        assert all(r is False for r in results)

    def test_backoff_allows_after_interval(self):
        # 1 unanswered = 4h interval. Last proactive 5h ago = allowed
        user_ts = time.time() - 10 * 3600  # IDLE
        proactive_ts = time.time() - 5 * 3600  # 5h ago
        results = [should_send_now(14, proactive_ts, user_ts, unanswered_count=1) for _ in range(100)]
        assert any(r is True for r in results)

    def test_none_timestamps_allows(self):
        # First ever proactive — no timestamps = IDLE, no interval check
        results = [should_send_now(14, None, None) for _ in range(100)]
        assert any(r is True for r in results)


# ---------------------------------------------------------------------------
# Mood detection
# ---------------------------------------------------------------------------


def _msg(content: str, user: str = "testuser") -> dict:
    return {"user_name": user, "role": "user", "content": content, "timestamp": time.time()}


class TestMoodDetection:
    def test_empty_messages_neutral(self):
        assert _detect_conversation_mood([]) == "neutral"

    def test_heavy_mood_detected(self):
        msgs = [
            _msg("Estoy procesando el duelo de perder a Brenda"),
            _msg("La culpa me está matando, es un trauma"),
            _msg("El ghosting fue horrible"),
        ]
        assert _detect_conversation_mood(msgs) == "heavy"

    def test_casual_mood_detected(self):
        msgs = [
            _msg("jajajaja no mames"),
            _msg("Estoy jugando el nuevo game que salió"),
            _msg("lol qué chistoso"),
        ]
        assert _detect_conversation_mood(msgs) == "casual"

    def test_intellectual_mood_from_long_messages(self):
        # Long messages without heavy or casual markers
        long_text = "a" * 200
        msgs = [_msg(long_text) for _ in range(5)]
        assert _detect_conversation_mood(msgs) == "intellectual"

    def test_neutral_short_normal_messages(self):
        msgs = [_msg("hola"), _msg("que tal"), _msg("bien")]
        assert _detect_conversation_mood(msgs) == "neutral"

    def test_heavy_takes_priority_over_casual(self):
        msgs = [
            _msg("jajaja pero la verdad el trauma me afecta"),
            _msg("el duelo está cabrón, la culpa no se va"),
        ]
        assert _detect_conversation_mood(msgs) == "heavy"


# ---------------------------------------------------------------------------
# Topic extraction
# ---------------------------------------------------------------------------


class TestTopicExtraction:
    def test_empty_returns_empty(self):
        assert _extract_conversation_topics([]) == ""

    def test_extracts_user_and_content(self):
        msgs = [_msg("hola mundo", user="Bernard")]
        result = _extract_conversation_topics(msgs)
        assert "Bernard: hola mundo" in result

    def test_truncates_long_messages(self):
        msgs = [_msg("x" * 500)]
        result = _extract_conversation_topics(msgs)
        assert len(result.split(": ", 1)[1]) <= 300

    def test_uses_last_10_messages(self):
        msgs = [_msg(f"msg{i}") for i in range(20)]
        result = _extract_conversation_topics(msgs)
        assert "msg10" in result
        assert "msg0" not in result

    def test_assistant_role_marked_as_self(self):
        """The bot's own past turns are labeled YOU so the model
        cannot mistake them for utterances from a third party named
        Insult living in the chat."""
        msgs = [
            _msg("Ve el lado positivo", user="bernard2389"),
            {
                "user_name": "Insult",
                "role": "assistant",
                "content": "Eso no es optimismo, eso es anestesia.",
                "timestamp": time.time(),
            },
        ]
        result = _extract_conversation_topics(msgs)
        assert "bernard2389: Ve el lado positivo" in result
        assert "YOU (Insult): Eso no es optimismo" in result
        # And critically, the assistant message MUST NOT appear with
        # "Insult: ..." (no YOU prefix) — that's the failure mode.
        assert "Insult: Eso no es optimismo" not in result

    def test_self_label_is_overridable(self):
        msgs = [
            {
                "user_name": "Insult",
                "role": "assistant",
                "content": "x",
                "timestamp": time.time(),
            }
        ]
        result = _extract_conversation_topics(msgs, self_label="MOI (BOT)")
        assert "MOI (BOT): x" in result


class TestParticipantExtraction:
    def test_empty_returns_empty(self):
        assert _extract_participants([]) == []

    def test_excludes_assistant_role(self):
        msgs = [
            _msg("hi", user="bernard"),
            {"user_name": "Insult", "role": "assistant", "content": "x", "timestamp": time.time()},
        ]
        assert _extract_participants(msgs) == ["bernard"]

    def test_dedupes_preserving_first_seen_order(self):
        msgs = [
            _msg("a", user="alex"),
            _msg("b", user="bernard"),
            _msg("c", user="alex"),
        ]
        assert _extract_participants(msgs) == ["alex", "bernard"]


# ---------------------------------------------------------------------------
# Proactive prompt shape — identity-anchored framing
# ---------------------------------------------------------------------------


class TestProactivePromptShape:
    """Verify the user_prompt handed to the LLM contains the structural
    cues that prevent the 2026-05-07 speaker-confusion bug.

    The bug: proactive_social produced *"bernard2389 sigue creyendo en
    el lado positivo o ya lo convenciste"* — third-person narration of
    the only active interlocutor. RCA showed the prompt formatted user
    and assistant rows symmetrically (`{name}: {content}`) and never
    explicitly told the model who YOU was. These tests pin the new
    shape so a future refactor cannot regress silently.
    """

    @pytest.mark.asyncio
    async def test_prompt_contains_participants_and_self_anchor(self):
        from unittest.mock import AsyncMock, MagicMock

        captured: dict = {}

        async def _fake_chat(system, messages, **kw):
            captured["system"] = system
            captured["messages"] = messages
            resp = MagicMock()
            resp.text = "tú sigues creyendo en el lado positivo o ya te convencí"
            resp.model_used = "claude-sonnet-4-6"
            return resp

        judge = MagicMock()
        judge.utility_call = AsyncMock(side_effect=_fake_chat)

        # Literal recent_messages from the bug turn.
        recent = [
            _msg("Ve el lado positivo", user="bernard2389"),
            {
                "user_name": "Insult",
                "role": "assistant",
                "content": "Eso no es optimismo, eso es anestesia.",
                "timestamp": time.time(),
            },
        ]
        user_facts = {"bernard2389": [{"fact": "lives in CDMX"}]}

        out = await generate_proactive_message(
            judge=judge,
            model="claude-sonnet-4-6",
            time_str="2026-05-07 22:28 CDMX",
            user_facts=user_facts,
            recent_messages=recent,
        )
        assert out  # round-trip succeeded

        # The user_prompt the LLM receives is the first (and only) message.
        assert "messages" in captured
        prompt = captured["messages"][0]["content"]

        # Identity scaffolding — Participants section
        assert "Participants in this thread:" in prompt
        assert "bernard2389 (human user)" in prompt
        assert "YOU (Insult)" in prompt
        assert "NOT a third party" in prompt

        # Recent exchange labels the bot's own turn as YOU
        assert "YOU (Insult): Eso no es optimismo" in prompt
        # Bernard's turn stays as the name — he IS the human interlocutor
        assert "bernard2389: Ve el lado positivo" in prompt

        # Closing directive — the regression-shaped instruction
        assert "second person" in prompt
        assert "third person" in prompt
        # Quote the literal failure mode so the model has the exact
        # pattern to refuse.
        assert "bernard2389 sigue creyendo" in prompt

    @pytest.mark.asyncio
    async def test_prompt_handles_empty_recent_messages(self):
        """No history should still produce a syntactically valid prompt
        — the runner falls back to a no-history placeholder rather than
        raising."""
        from unittest.mock import AsyncMock, MagicMock

        captured: dict = {}

        async def _fake_chat(system, messages, **kw):
            captured["messages"] = messages
            resp = MagicMock()
            resp.text = "siguen vivos?"
            resp.model_used = "claude-sonnet-4-6"
            return resp

        judge = MagicMock()
        judge.utility_call = AsyncMock(side_effect=_fake_chat)

        out = await generate_proactive_message(
            judge=judge,
            model="claude-sonnet-4-6",
            time_str="now",
            user_facts={},
            recent_messages=[],
        )
        assert out
        prompt = captured["messages"][0]["content"]
        assert "(no recent messages)" in prompt
        # Even with no users active, the YOU-anchor still appears.
        assert "YOU (Insult)" in prompt


# ---------------------------------------------------------------------------
# Search topic selection
# ---------------------------------------------------------------------------


class TestPickSearchTopic:
    def test_heavy_mood_returns_psychology_topic(self):
        topic = _pick_search_topic({}, "heavy", "")
        # Should be from _MOOD_TOPICS["heavy"]
        heavy_keywords = ["psychology", "humanist", "emotional", "personal growth", "stoic", "attachment", "boundary"]
        assert any(kw in topic.lower() for kw in heavy_keywords)

    def test_casual_mood_returns_casual_topic(self):
        topic = _pick_search_topic({}, "casual", "")
        casual_keywords = ["gaming", "internet", "technology", "entertainment", "mexico"]
        assert any(kw in topic.lower() for kw in casual_keywords)

    def test_neutral_mood_with_facts_uses_interests(self):
        facts = {"Bernard": [{"fact": "Bernard is a programmer who loves gaming"}]}
        topic = _pick_search_topic(facts, "neutral", "")
        # Should match programming or gaming from facts
        assert topic  # Just ensure it returns something

    def test_neutral_mood_no_facts_returns_default(self):
        topic = _pick_search_topic({}, "neutral", "")
        assert topic  # Returns a default topic

    def test_substring_art_does_not_match_parte_or_departamento(self):
        """Regression: pre-v3.7.10 the keyword 'art' substring-matched
        'parte' / 'departamento' / 'artista' / 'reportar' etc., so almost
        every neutral-mood world_scan picked the lone art topic and the
        bot kept inviting users to museums. Ensure word boundaries hold."""
        boring_text = "Ya está la reserva del departamento. Te paso una parte del reporte después."
        # No facts → if 'art' still substring-matches, this returns the art bucket;
        # otherwise it falls through to _DEFAULT_TOPICS.
        # We can't assert which default it returns (random), but we CAN assert
        # the result is NOT in the art bucket.
        topic = _pick_search_topic({}, "neutral", boring_text)
        assert "art exhibitions" not in topic
        assert "documentary photography" not in topic

    def test_word_arte_matches_art_bucket(self):
        """Counterpart to the regression test: real mentions of 'arte'
        SHOULD still trigger the cultural-topics bucket."""
        topic = _pick_search_topic({}, "neutral", "Vamos a ver una expo de arte contemporáneo")
        # Bucket has 6 entries, all are cultural — at least one of these
        # keywords must appear.
        cultural_keywords = ["art exhibitions", "cinema", "literature", "theater", "music", "photography"]
        assert any(kw in topic for kw in cultural_keywords)


# ---------------------------------------------------------------------------
# Elapsed description
# ---------------------------------------------------------------------------


class TestElapsedDescription:
    def test_none_returns_unknown(self):
        assert _elapsed_description(None) == "unknown time"

    def test_minutes(self):
        ts = time.time() - 30 * 60
        result = _elapsed_description(ts)
        assert "minutos" in result

    def test_hours(self):
        ts = time.time() - 5 * 3600
        result = _elapsed_description(ts)
        assert "horas" in result

    def test_days(self):
        ts = time.time() - 3 * 86400
        result = _elapsed_description(ts)
        assert "dias" in result


# ---------------------------------------------------------------------------
# Language consistency anti-patterns
# ---------------------------------------------------------------------------


class TestLanguageAntiPatterns:
    """Verify the new language consistency patterns in character.py."""

    @pytest.fixture()
    def detect(self):
        from insult.core.character import detect_anti_patterns

        return detect_anti_patterns

    def test_detects_english_sentence_starting_with_but(self, detect):
        text = "But Bernard, this video is INTENSE. Pure anger, zero diplomatic approach."
        matches = detect(text)
        assert len(matches) > 0

    def test_detects_english_sentence_starting_with_this_is(self, detect):
        text = "This is exactly what I was talking about yesterday in the conversation."
        matches = detect(text)
        assert len(matches) > 0

    def test_allows_spanish_with_english_words(self, detect):
        # Single English words embedded in Spanish = OK
        text = "Eso es un classic pattern de evasion, bro"
        matches = detect(text)
        # Should not trigger language patterns (may trigger others, filter)
        lang_patterns = [m for m in matches if "But " in m or "This is" in m or "that probably" in m]
        assert len(lang_patterns) == 0

    def test_detects_that_probably_pattern(self, detect):
        text = "that probably resonated with your experience of being called aggressive vegan"
        matches = detect(text)
        assert len(matches) > 0

    def test_allows_short_english_fragments(self, detect):
        # Short fragments under 20 chars should not trigger
        text = "Es un vibe check"
        matches = detect(text)
        lang_patterns = [m for m in matches if "But " in m or "This is" in m]
        assert len(lang_patterns) == 0
