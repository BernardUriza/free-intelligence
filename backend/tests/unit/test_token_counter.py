"""Unit tests for token_counter module.

Tests token estimation utility for LLM operations.
"""

from __future__ import annotations

import pytest
from backend.utils.token_counter import TokenCounter


class TestTokenCounterInit:
    """Tests for TokenCounter initialization."""

    def test_default_tokens_per_word(self) -> None:
        """Default tokens_per_word is 1.3 (GPT-4 heuristic)."""
        counter = TokenCounter()
        assert counter.tokens_per_word == 1.3

    def test_custom_tokens_per_word(self) -> None:
        """Custom tokens_per_word can be set."""
        counter = TokenCounter(tokens_per_word=2.0)
        assert counter.tokens_per_word == 2.0


class TestEstimateTokens:
    """Tests for estimate_tokens method."""

    def test_empty_string_returns_zero(self) -> None:
        """Empty string returns 0 tokens."""
        counter = TokenCounter()
        assert counter.estimate_tokens("") == 0

    def test_whitespace_only_returns_zero(self) -> None:
        """Whitespace-only string returns 0 tokens."""
        counter = TokenCounter()
        assert counter.estimate_tokens("   ") == 0
        assert counter.estimate_tokens("\t\n") == 0

    def test_none_returns_zero(self) -> None:
        """None returns 0 tokens (falsy check)."""
        counter = TokenCounter()
        assert counter.estimate_tokens(None) == 0  # type: ignore[arg-type]

    def test_single_word_minimum_one_token(self) -> None:
        """Single word returns at least 1 token."""
        counter = TokenCounter()
        result = counter.estimate_tokens("hello")
        assert result >= 1

    def test_multiple_words_uses_heuristic(self) -> None:
        """Multiple words apply 1.3 multiplier."""
        counter = TokenCounter()
        # 10 words * 1.3 = 13 tokens
        result = counter.estimate_tokens("one two three four five six seven eight nine ten")
        assert result == 13

    def test_custom_multiplier_applied(self) -> None:
        """Custom tokens_per_word multiplier is applied."""
        counter = TokenCounter(tokens_per_word=2.0)
        # 5 words * 2.0 = 10 tokens
        result = counter.estimate_tokens("one two three four five")
        assert result == 10

    def test_returns_integer(self) -> None:
        """Result is always an integer."""
        counter = TokenCounter()
        result = counter.estimate_tokens("hello world test")
        assert isinstance(result, int)

    def test_model_parameter_ignored(self) -> None:
        """Model parameter is accepted but currently ignored."""
        counter = TokenCounter()
        # Should not raise and return same result regardless of model
        result1 = counter.estimate_tokens("hello world")
        result2 = counter.estimate_tokens("hello world", _model="gpt-4")
        result3 = counter.estimate_tokens("hello world", _model="claude-3")
        assert result1 == result2 == result3

    def test_unicode_text(self) -> None:
        """Unicode text is handled properly."""
        counter = TokenCounter()
        result = counter.estimate_tokens("Hola ¿cómo estás? Bien gracias")
        assert result > 0

    def test_long_text(self) -> None:
        """Long text is handled without error."""
        counter = TokenCounter()
        long_text = " ".join(["word"] * 1000)  # 1000 words
        result = counter.estimate_tokens(long_text)
        assert result == 1300  # 1000 * 1.3


class TestEstimateTokensBatch:
    """Tests for estimate_tokens_batch method."""

    def test_empty_list_returns_empty(self) -> None:
        """Empty list returns empty list."""
        counter = TokenCounter()
        assert counter.estimate_tokens_batch([]) == []

    def test_single_text(self) -> None:
        """Single text returns list with one result."""
        counter = TokenCounter()
        result = counter.estimate_tokens_batch(["hello world"])
        assert len(result) == 1
        assert result[0] > 0

    def test_multiple_texts(self) -> None:
        """Multiple texts return corresponding token counts."""
        counter = TokenCounter()
        texts = ["hello", "hello world", "one two three"]
        result = counter.estimate_tokens_batch(texts)
        assert len(result) == 3
        # Longer texts should have more tokens
        assert result[2] > result[0]

    def test_mixed_content(self) -> None:
        """Mixed content (empty, normal, long) handled."""
        counter = TokenCounter()
        texts = ["", "hello", "one two three four five"]
        result = counter.estimate_tokens_batch(texts)
        assert result[0] == 0  # Empty
        assert result[1] >= 1  # Single word
        assert result[2] == 6  # 5 words * 1.3 = 6.5 → 6

    def test_model_parameter_ignored(self) -> None:
        """Model parameter is accepted but ignored."""
        counter = TokenCounter()
        texts = ["hello", "world"]
        result1 = counter.estimate_tokens_batch(texts)
        result2 = counter.estimate_tokens_batch(texts, _model="gpt-4")
        assert result1 == result2
