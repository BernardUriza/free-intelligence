"""
Free Intelligence - Token Counter Utility

Centralized token estimation using GPT-4 heuristic.

File: backend/utils/token_counter.py
Created: 2025-10-29
Card: FI-CORE-REF-002

Features:
- Single source of truth for token counting
- GPT-4 heuristic: ~1.3 tokens per word
- Handles edge cases (empty, unicode, very long text)
- Injectable dependency (no global state)
"""


class TokenCounter:
    """
    Token counter using GPT-4 heuristic.

    Estimates tokens for LLM operations without calling external APIs.
    """

    def __init__(self, tokens_per_word: float = 1.3):
        """
        Initialize token counter.

        Args:
            tokens_per_word: Multiplier for word count (default: 1.3 for GPT-4 heuristic)
        """
        self.tokens_per_word = tokens_per_word

    def estimate_tokens(self, text: str, model: str = None) -> int:
        """
        Estimate token count for text.

        Uses word count heuristic: tokens ≈ words * 1.3

        Args:
            text: Input text
            model: Model name (optional, for future model-specific logic)

        Returns:
            Estimated token count (integer)
        """
        if not text or not text.strip():
            return 0

        # Count words (split on whitespace)
        word_count = len(text.split())

        # Apply heuristic
        estimated_tokens = int(word_count * self.tokens_per_word)

        return max(estimated_tokens, 1)  # Minimum 1 token for non-empty text

    def estimate_tokens_batch(self, texts: list[str], model: str = None) -> list[int]:
        """
        Estimate tokens for multiple texts.

        Args:
            texts: List of input texts
            model: Model name (optional)

        Returns:
            List of estimated token counts
        """
        return [self.estimate_tokens(text, model) for text in texts]
