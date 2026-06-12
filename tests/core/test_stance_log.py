"""Tests for insult.core.stance_log — bot position tracking."""

import time

from personas.insult.core.stance_log import (
    MAX_STANCES_PER_CONTEXT,
    _extract_topic,
    build_stance_prompt,
    evict_old_stances,
    extract_stances,
)

# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _ts() -> float:
    return time.time()


# ═══════════════════════════════════════════════════════════════════════════
# Extraction Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestExtractStances:
    def test_skips_low_assertion_density(self):
        result = extract_stances("El capitalismo es un sistema roto.", 0.3, _ts())
        assert result.skipped is True
        assert result.entries == []

    def test_extracts_from_high_density(self):
        text = "El capitalismo es un sistema obsoleto. La democracia está comprometida por intereses corporativos."
        result = extract_stances(text, 0.6, _ts())
        assert result.skipped is False
        assert len(result.entries) >= 1
        # Should have extracted topic keywords
        for entry in result.entries:
            assert entry.topic
            assert entry.position
            assert 0.0 < entry.confidence <= 1.0

    def test_extracts_bold_sententia(self):
        text = "**El arte verdadero es subversión**. Todo lo demás es decoración barata."
        result = extract_stances(text, 0.7, _ts())
        assert result.skipped is False
        # Bold sententia should get higher confidence (0.6 base + 0.2 bold)
        bold_entries = [e for e in result.entries if e.confidence >= 0.8]
        assert len(bold_entries) >= 1

    def test_extracts_negation(self):
        text = "The economy is not sustainable. This system never works for everyone."
        result = extract_stances(text, 0.5, _ts())
        assert result.skipped is False
        # Negation patterns should be detected
        negation_entries = [e for e in result.entries if e.confidence >= 0.8]
        assert len(negation_entries) >= 1

    def test_max_3_stances_per_response(self):
        text = (
            "El capitalismo es un desastre. "
            "La política es una farsa. "
            "La educación está destruida. "
            "La cultura es mercancía. "
            "El futuro está perdido."
        )
        result = extract_stances(text, 0.8, _ts())
        assert len(result.entries) <= 3

    def test_position_truncation(self):
        long_sentence = "El capitalismo es " + "muy " * 100 + "malo."
        assert len(long_sentence) > 200
        result = extract_stances(long_sentence, 0.7, _ts())
        for entry in result.entries:
            assert len(entry.position) <= 200

    def test_confidence_scoring(self):
        # Base assertion: 0.6
        base_text = "El sistema es corrupto."
        result_base = extract_stances(base_text, 0.5, _ts())
        if result_base.entries:
            assert result_base.entries[0].confidence == 0.6

        # Bold: 0.6 + 0.2 = 0.8
        bold_text = "**El sistema es corrupto**."
        result_bold = extract_stances(bold_text, 0.5, _ts())
        if result_bold.entries:
            assert result_bold.entries[0].confidence == 0.8

        # Negation: 0.6 + 0.2 = 0.8
        neg_text = "El sistema no es justo para nadie."
        result_neg = extract_stances(neg_text, 0.5, _ts())
        if result_neg.entries:
            assert result_neg.entries[0].confidence == 0.8

        # Bold + negation: 0.6 + 0.2 + 0.2 = 1.0
        both_text = "**El sistema no es justo para nadie**."
        result_both = extract_stances(both_text, 0.5, _ts())
        if result_both.entries:
            assert result_both.entries[0].confidence == 1.0


class TestTopicExtraction:
    def test_topic_extraction(self):
        topic = _extract_topic("El capitalismo moderno es un sistema roto.")
        words = topic.split()
        # Should have 2-4 keywords
        assert 2 <= len(words) <= 4
        # Stopwords should be removed
        for stopword in ("el", "es", "un"):
            assert stopword not in words

    def test_returns_empty_for_short_sentence(self):
        topic = _extract_topic("Es malo.")
        # Only one content word after filtering, needs at least 2
        assert topic == ""

    def test_deduplicates_keywords(self):
        topic = _extract_topic("The system breaks the system every time the system fails.")
        words = topic.split()
        assert len(words) == len(set(words))


# ═══════════════════════════════════════════════════════════════════════════
# Prompt Building Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestBuildStancePrompt:
    def test_build_stance_prompt_empty(self):
        result = build_stance_prompt([])
        assert result == ""

    def test_build_stance_prompt_with_stances(self):
        stances = [
            {
                "topic": "capitalismo sistema",
                "position": "El capitalismo es un sistema roto",
                "confidence": 0.8,
                "timestamp": 1000.0,
            },
            {
                "topic": "educacion publica",
                "position": "La educacion publica necesita reforma total",
                "confidence": 0.6,
                "timestamp": 1001.0,
            },
        ]
        result = build_stance_prompt(stances)
        assert "## Your Prior Positions" in result
        assert "capitalismo sistema" in result
        assert "educacion publica" in result
        assert "confidence: 0.8" in result
        assert "confidence: 0.6" in result

    def test_build_stance_prompt_max_5(self):
        stances = [
            {
                "topic": f"topic {i}",
                "position": f"Position {i}",
                "confidence": 0.5,
                "timestamp": float(i),
            }
            for i in range(10)
        ]
        result = build_stance_prompt(stances)
        # Should only include 5 stances (the most recent ones)
        line_count = result.count("- [")
        assert line_count == 5


# ═══════════════════════════════════════════════════════════════════════════
# Eviction Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestEviction:
    def test_evict_old_stances(self):
        stances = [{"topic": f"topic {i}", "position": f"pos {i}", "timestamp": float(i)} for i in range(30)]
        result = evict_old_stances(stances)
        assert len(result) == MAX_STANCES_PER_CONTEXT
        # Should keep the newest ones (highest timestamps)
        timestamps = [s["timestamp"] for s in result]
        assert min(timestamps) == 10.0  # 30 - 20 = 10
        assert max(timestamps) == 29.0

    def test_evict_when_under_limit(self):
        stances = [{"topic": f"topic {i}", "position": f"pos {i}", "timestamp": float(i)} for i in range(5)]
        result = evict_old_stances(stances)
        assert len(result) == 5
        assert result == stances  # unchanged
