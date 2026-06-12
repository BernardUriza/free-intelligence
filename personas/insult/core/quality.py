"""Post-generation quality validator — rule-based response quality checks.

Checks whether a bot response provides actual conversational value rather
than being obvious, parroting, or empty.  All checks are rule-based (zero
LLM cost).  Results are telemetry-only — they do NOT block responses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

from personas.insult.core.patterns import COMMON_STOPWORDS

log = structlog.get_logger()

# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

_WORD_RE = re.compile(r"[a-záéíóúüñ]+", re.IGNORECASE)

_QUALITY_STOPWORDS = COMMON_STOPWORDS | {
    "los",
    "las",
    "por",
    "con",
    "para",
    "del",
    "al",
    "me",
    "te",
    "mi",
    "tu",
    "su",
    "ya",
    "si",
    "mas",
    "pero",
    "como",
    "esta",
    "esto",
    "eso",
    "are",
    "not",
    "this",
    "that",
    "and",
    "but",
    "for",
    "was",
    "with",
    "you",
    "your",
    "can",
    "have",
    "has",
    "had",
    "been",
    "will",
}

_CHALLENGE_WORDS = {
    "pero",
    "sin embargo",
    "really",
    "de verdad",
    "en serio",
    "no crees que",
    "seguro que",
}

_REFRAMING_PHRASES = {
    "o sea",
    "lo que realmente",
    "the real issue",
    "en otras palabras",
    "dicho de otro modo",
}

# Threshold for "new content words" to consider a response non-obvious
_NEW_WORDS_THRESHOLD = 5

# Jaccard similarity above which a response may be flagged as obvious
_JACCARD_OBVIOUS_THRESHOLD = 0.4

# How many times a shape can repeat before flagging structural variety
_SHAPE_REPEAT_LIMIT = 3

# How many recent shapes to consider
_RECENT_SHAPES_WINDOW = 5


# ═══════════════════════════════════════════════════════════════════════════
# Dataclass
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class QualityCheck:
    """Result of a post-generation quality check."""

    has_value_move: bool  # does it clarify, deepen, challenge, or discover?
    is_obvious: bool  # is it just paraphrasing what the user said?
    structural_variety_ok: bool  # is it not repeating the same structure?
    violations: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _content_words(text: str) -> set[str]:
    """Extract content words (lowercased, stopwords removed)."""
    words = _WORD_RE.findall(text.lower())
    return {w for w in words if w not in _QUALITY_STOPWORDS}


def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard similarity between two sets."""
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


# ═══════════════════════════════════════════════════════════════════════════
# Value move detection
# ═══════════════════════════════════════════════════════════════════════════


def _has_challenge(response: str) -> bool:
    """Check if response challenges the user (question + challenge word)."""
    if "?" not in response:
        return False
    resp_lower = response.lower()
    return any(word in resp_lower for word in _CHALLENGE_WORDS)


def _has_deepening(
    response_words: set[str],
    user_words: set[str],
) -> bool:
    """Check if response introduces 5+ new content words."""
    new_words = response_words - user_words
    return len(new_words) >= _NEW_WORDS_THRESHOLD


def _has_discovery(response: str, user_words: set[str]) -> bool:
    """Check if response asks a genuinely new question."""
    # Find sentences that end with '?'
    questions = re.findall(r"[^.!?]*\?", response)
    for question in questions:
        question_words = _content_words(question)
        new_in_question = question_words - user_words
        if new_in_question:
            return True
    return False


def _has_clarification(response: str) -> bool:
    """Check if response uses reframing language."""
    resp_lower = response.lower()
    return any(phrase in resp_lower for phrase in _REFRAMING_PHRASES)


def _detect_value_move(
    response: str,
    user_message: str,
    response_words: set[str],
    user_words: set[str],
) -> bool:
    """Return True if the response has at least one value move."""
    if _has_challenge(response):
        return True
    if _has_deepening(response_words, user_words):
        return True
    if _has_discovery(response, user_words):
        return True
    return bool(_has_clarification(response))


# ═══════════════════════════════════════════════════════════════════════════
# Obviousness detection
# ═══════════════════════════════════════════════════════════════════════════


def _detect_obvious(
    response_words: set[str],
    user_words: set[str],
    jaccard: float,
) -> bool:
    """Flag if response mostly parrots the user message."""
    new_words = response_words - user_words
    return jaccard > _JACCARD_OBVIOUS_THRESHOLD and len(new_words) < _NEW_WORDS_THRESHOLD


# ═══════════════════════════════════════════════════════════════════════════
# Structural variety
# ═══════════════════════════════════════════════════════════════════════════


def _check_structural_variety(
    response: str,
    recent_shapes: list[str],
) -> bool:
    """Return True if structural variety is OK (shape not over-repeated)."""
    if not recent_shapes:
        return True
    # Determine current shape — use first 20 chars as rough fingerprint
    # In practice the caller passes shape labels from ExpressionHistory
    # so we just check repetition count.
    window = recent_shapes[-_RECENT_SHAPES_WINDOW:]
    if not window:
        return True
    # The "current" shape is the last one in the list
    current_shape = window[-1] if window else ""
    count = sum(1 for s in window if s == current_shape)
    return count < _SHAPE_REPEAT_LIMIT


# ═══════════════════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════════════════


def check_quality(
    response: str,
    user_message: str,
    recent_shapes: list[str],
    agreement_streak: int = 0,
) -> QualityCheck:
    """Check response quality.  Returns QualityCheck with diagnostic info.

    This is telemetry-only — it does NOT block responses.
    """
    response_words = _content_words(response)
    user_words = _content_words(user_message)
    new_words = response_words - user_words

    jaccard = _jaccard_similarity(user_words, response_words)

    has_value_move = _detect_value_move(
        response,
        user_message,
        response_words,
        user_words,
    )
    is_obvious = _detect_obvious(response_words, user_words, jaccard)
    structural_variety_ok = _check_structural_variety(response, recent_shapes)

    violations: list[str] = []

    if not has_value_move:
        violations.append("no_value_move: response lacks challenge, depth, discovery, or reframing")

    if is_obvious:
        violations.append("obvious_paraphrase: high overlap with user message, few new words")

    if not structural_variety_ok:
        violations.append("structural_repetition: same shape used 3+ times in recent responses")

    if agreement_streak >= 2:
        violations.append(f"agreement_streak_high: {agreement_streak} consecutive agreements")

    result = QualityCheck(
        has_value_move=has_value_move,
        is_obvious=is_obvious,
        structural_variety_ok=structural_variety_ok,
        violations=violations,
    )

    log.info(
        "quality_check",
        has_value_move=has_value_move,
        is_obvious=is_obvious,
        structural_variety_ok=structural_variety_ok,
        violation_count=len(violations),
        jaccard_score=round(jaccard, 2),
        new_words_count=len(new_words),
    )

    return result
