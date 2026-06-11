"""Stance tracking — prevents bot flip-flopping on stated positions.

Extracts assertions from bot responses and stores them as stances with
topic keywords and confidence scores. All extraction is regex/heuristic
based — zero LLM cost.

Stances are stored via memory.py (this module has no DB access).
Max 20 stances per user-channel pair with FIFO eviction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

from insult.core.patterns import COMMON_STOPWORDS
from insult.core.prompts_loader import load_prompt

log = structlog.get_logger()

# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

MAX_STANCES_PER_CONTEXT = 20
_MAX_POSITION_LENGTH = 200
_MAX_STANCES_PER_RESPONSE = 3
_MIN_ASSERTION_DENSITY = 0.4
_MAX_STANCES_IN_PROMPT = 5

_STANCE_STOPWORDS = COMMON_STOPWORDS | {
    "los",
    "las",
    "por",
    "con",
    "para",
    "del",
    "al",
    "are",
    "not",
    "this",
    "that",
    "and",
    "but",
    "for",
    "was",
    "with",
}

# Assertion patterns — strong declarative statements
_ASSERTION_PATTERNS_ES = re.compile(
    r"\b(?:es|son|está|están|será|serán|fue|fueron)\s+\w+",
    re.IGNORECASE,
)
_ASSERTION_PATTERNS_EN = re.compile(
    r"\b(?:the|this|that|it)\s+(?:is|are|was|were)\b",
    re.IGNORECASE,
)
_BOLD_SENTENTIA = re.compile(r"\*\*(.+?)\*\*")
_NEGATION_PATTERNS = re.compile(
    r"\b(?:no\s+es|nunca|jamás|is\s+not|isn't|are\s+not|aren't|never|cannot|can't)\b",
    re.IGNORECASE,
)

# Sentence splitting
_SENTENCE_SPLIT = re.compile(r"[.!?]+\s*|\n+")

# Word extraction for topics (letters, accented chars)
_WORD_RE = re.compile(r"[a-záéíóúñüA-ZÁÉÍÓÚÑÜ]{3,}", re.IGNORECASE)


# ═══════════════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class StanceEntry:
    topic: str  # normalized topic keywords (e.g., "capitalismo sistema")
    position: str  # what Insult said (max 200 chars)
    confidence: float  # 0.0-1.0 based on assertion strength
    timestamp: float


@dataclass
class StanceExtraction:
    entries: list[StanceEntry] = field(default_factory=list)
    skipped: bool = False  # True if response was too short/vague to extract


# ═══════════════════════════════════════════════════════════════════════════
# Topic extraction
# ═══════════════════════════════════════════════════════════════════════════


def _extract_topic(sentence: str) -> str:
    """Extract 2-4 content keywords from a sentence as topic key."""
    words = _WORD_RE.findall(sentence)
    keywords = [w.lower() for w in words if w.lower() not in _STANCE_STOPWORDS]
    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    # Keep 2-4 keywords
    selected = unique[:4]
    if len(selected) < 2:
        return ""
    return " ".join(selected)


# ═══════════════════════════════════════════════════════════════════════════
# Stance extraction
# ═══════════════════════════════════════════════════════════════════════════


def _score_sentence(sentence: str) -> tuple[float, bool, bool]:
    """Score a sentence's assertion strength.

    Returns (confidence, has_bold, has_negation).
    """
    has_bold = bool(_BOLD_SENTENTIA.search(sentence))
    has_negation = bool(_NEGATION_PATTERNS.search(sentence))

    has_assertion = bool(_ASSERTION_PATTERNS_ES.search(sentence) or _ASSERTION_PATTERNS_EN.search(sentence))

    if not has_assertion and not has_bold and not has_negation:
        return 0.0, False, False

    confidence = 0.6
    if has_bold:
        confidence += 0.2
    if has_negation:
        confidence += 0.2
    return min(confidence, 1.0), has_bold, has_negation


def extract_stances(
    response_text: str,
    assertion_density: float,
    timestamp: float,
) -> StanceExtraction:
    """Extract stated positions from a bot response.

    Only extracts if assertion_density >= 0.4 (the response makes clear claims).
    Returns 0-3 StanceEntry items.
    """
    if assertion_density < _MIN_ASSERTION_DENSITY:
        return StanceExtraction(entries=[], skipped=True)

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(response_text) if s.strip()]

    candidates: list[StanceEntry] = []
    for sentence in sentences:
        confidence, _has_bold, _has_negation = _score_sentence(sentence)
        if confidence <= 0.0:
            continue

        topic = _extract_topic(sentence)
        if not topic:
            continue

        position = sentence[:_MAX_POSITION_LENGTH]
        candidates.append(
            StanceEntry(
                topic=topic,
                position=position,
                confidence=confidence,
                timestamp=timestamp,
            )
        )

    # Sort by confidence descending, take top 3
    candidates.sort(key=lambda s: s.confidence, reverse=True)
    entries = candidates[:_MAX_STANCES_PER_RESPONSE]

    if entries:
        log.debug(
            "stances_extracted",
            count=len(entries),
            topics=[e.topic for e in entries],
        )

    return StanceExtraction(entries=entries, skipped=False)


# ═══════════════════════════════════════════════════════════════════════════
# Prompt building
# ═══════════════════════════════════════════════════════════════════════════


def build_stance_prompt(stances: list[dict]) -> str:
    """Build system prompt section with bot's prior positions.

    Args:
        stances: list of dicts from memory (topic, position, confidence, timestamp)

    Returns prompt section or empty string if no stances.
    """
    if not stances:
        return ""

    # Sort by timestamp descending, then confidence descending
    sorted_stances = sorted(
        stances,
        key=lambda s: (s.get("timestamp", 0), s.get("confidence", 0)),
        reverse=True,
    )
    selected = sorted_stances[:_MAX_STANCES_IN_PROMPT]

    lines = [load_prompt("stance_prior_positions_header")]
    for s in selected:
        topic = s.get("topic", "unknown")
        position = s.get("position", "")
        confidence = s.get("confidence", 0.0)
        lines.append(f'- [{topic}]: "{position}" (confidence: {confidence})')

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# FIFO eviction
# ═══════════════════════════════════════════════════════════════════════════


def evict_old_stances(stances: list[dict]) -> list[dict]:
    """Keep only the newest MAX_STANCES_PER_CONTEXT stances."""
    if len(stances) <= MAX_STANCES_PER_CONTEXT:
        return stances

    sorted_stances = sorted(
        stances,
        key=lambda s: s.get("timestamp", 0),
        reverse=True,
    )
    return sorted_stances[:MAX_STANCES_PER_CONTEXT]
