"""
Test suite for TokenCounter utility.

File: tests/test_token_counter.py
Created: 2025-10-29
Card: FI-CORE-REF-002

Tests:
- Empty text handling
- Short text (1-10 words)
- Long text (100+ words)
- Unicode/emoji handling
- Batch estimation
"""

from backend.utils.token_counter import TokenCounter


class TestTokenCounter:
    """Test token counting utility."""

    def test_empty_text(self) -> None:
        """Test empty string returns 0 tokens."""
        counter = TokenCounter()
        assert counter.estimate_tokens("") == 0
        assert counter.estimate_tokens("   ") == 0  # Whitespace only

    def test_single_word(self) -> None:
        """Test single word estimation."""
        counter = TokenCounter()
        # 1 word * 1.3 = 1.3 → int(1.3) = 1
        assert counter.estimate_tokens("hello") == 1

    def test_short_text(self) -> None:
        """Test short text (5 words)."""
        counter = TokenCounter()
        text = "This is a short sentence"
        # 5 words * 1.3 = 6.5 → int(6.5) = 6
        assert counter.estimate_tokens(text) == 6

    def test_medium_text(self) -> None:
        """Test medium text (20 words)."""
        counter = TokenCounter()
        text = "The quick brown fox jumps over the lazy dog multiple times in this sentence to reach twenty words total"
        word_count = len(text.split())
        expected = int(word_count * 1.3)
        assert counter.estimate_tokens(text) == expected

    def test_long_text(self) -> None:
        """Test long text (100+ words)."""
        counter = TokenCounter()
        # Generate 100-word text
        text = " ".join(["word"] * 100)
        # 100 words * 1.3 = 130 tokens
        assert counter.estimate_tokens(text) == 130

    def test_unicode_text(self) -> None:
        """Test unicode and emoji handling."""
        counter = TokenCounter()
        text = "Hello 世界 🌍"
        # 3 "words" (split on whitespace) * 1.3 = 3.9 → 3
        assert counter.estimate_tokens(text) == 3

    def test_punctuation(self) -> None:
        """Test text with punctuation."""
        counter = TokenCounter()
        text = "Hello, world! How are you?"
        # Split on whitespace: ["Hello,", "world!", "How", "are", "you?"] = 5 words
        # 5 * 1.3 = 6.5 → 6
        assert counter.estimate_tokens(text) == 6

    def test_newlines(self) -> None:
        """Test text with newlines."""
        counter = TokenCounter()
        text = "Line one\nLine two\nLine three"
        # 6 words * 1.3 = 7.8 → 7
        assert counter.estimate_tokens(text) == 7

    def test_custom_multiplier(self) -> None:
        """Test custom tokens_per_word multiplier."""
        counter = TokenCounter(tokens_per_word=2.0)
        text = "five word test sentence here"
        # 5 words * 2.0 = 10 tokens
        assert counter.estimate_tokens(text) == 10

    def test_batch_estimation(self) -> None:
        """Test batch estimation for multiple texts."""
        counter = TokenCounter()
        texts = [
            "Short",
            "A bit longer text",
            "This is a much longer sentence with more words",
        ]

        results = counter.estimate_tokens_batch(texts)

        assert len(results) == 3
        assert results[0] == 1  # 1 word
        assert results[1] == 5  # 4 words * 1.3 = 5.2 → 5
        assert results[2] == 11  # 9 words * 1.3 = 11.7 → 11

    def test_batch_empty(self) -> None:
        """Test batch estimation with empty list."""
        counter = TokenCounter()
        assert counter.estimate_tokens_batch([]) == []

    def test_consistency(self) -> None:
        """Test consistent results for same input."""
        counter = TokenCounter()
        text = "Consistent token counting is important"

        result1 = counter.estimate_tokens(text)
        result2 = counter.estimate_tokens(text)

        assert result1 == result2

    def test_minimum_token_for_nonempty(self) -> None:
        """Test non-empty text always returns at least 1 token."""
        counter = TokenCounter()
        # Even a single character should return 1 token
        assert counter.estimate_tokens("a") >= 1
        assert counter.estimate_tokens("🌍") >= 1
