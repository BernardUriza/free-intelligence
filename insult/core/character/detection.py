"""Detection of identity-leak and assistant-drift patterns + reinforcement constants.

This module is a **composition layer** over ``fi_core.persona``:

- Generic patterns (English + Spanish AI disclosure, assistant tone,
  therapy-speak, summarizing, stage directions, markdown drift, moralizing,
  over-validation, clarification dump) live in ``fi_core.persona.packs`` and
  are imported here.
- Insult-persona-specific patterns and reinforcement strings live in
  ``_insult_patterns.py`` (private) and are merged on top.

The public surface (module-level constants and functions) is preserved
exactly so existing callsites in ``llm.chat``, ``character.prompts``,
and ``cogs`` continue to work without changes.

Three pattern families:

- ``CHARACTER_BREAK_PATTERNS`` — hard identity leaks (the model claiming to be
  an AI / Claude / a language model). Triggers a retry with a reinforced prompt
  and, on retry failure, sanitization of the offending sentences.
- ``ANTI_PATTERN_CHECKS`` — soft drift toward generic-assistant tone
  (customer-support framing, therapy-speak, summarizing) plus Insult-specific
  failure modes (cheerleading openers, pseudo-clinical claims, English-leak).
  Logged for monitoring; does not block the response.
- ``CLARIFICATION_DUMP_PATTERNS`` — the bot punting the task back at the user
  ("dime qué busco", "a qué te refieres") despite having context. Triggers a
  retry with ``CONTEXT_REINFORCEMENT`` appended.

Reinforcement strings + identity thresholds live here too because they belong
to the same failure-mode-and-remedy story; ``llm.chat`` and the prompt
builder both consume them.
"""

from __future__ import annotations

from fi_core.persona import (
    AntiPatternMonitor as _AntiPatternMonitor,
)
from fi_core.persona import (
    BreakDetector as _BreakDetector,
)
from fi_core.persona import (
    ClarificationDumpDetector as _ClarificationDumpDetector,
)
from fi_core.persona import packs as _packs
from fi_core.persona import sanitize as _sanitize

from insult.core.character._insult_patterns import (
    INSULT_ANTI_PATTERN_PATTERNS,
    INSULT_BREAK_PATTERNS,
    INSULT_CONTEXT_REINFORCEMENT,
    INSULT_IDENTITY_REINFORCEMENT_SUFFIX,
    INSULT_REINFORCEMENT,
)

# ============================================================
# Composed pattern lists (preserve original public names + semantics)
# ============================================================

CHARACTER_BREAK_PATTERNS = (
    _packs.GENERIC_AI_DISCLOSURE_EN
    + _packs.GENERIC_AI_DISCLOSURE_ES
    + INSULT_BREAK_PATTERNS
)

ANTI_PATTERN_CHECKS = (
    _packs.ASSISTANT_TONE_EN
    + _packs.ASSISTANT_TONE_ES
    + _packs.THERAPY_SPEAK_EN
    + _packs.THERAPY_SPEAK_ES
    + _packs.SUMMARIZING
    + _packs.STAGE_DIRECTIONS
    + _packs.MARKDOWN_DRIFT
    + _packs.MORALIZING_EN
    + _packs.MORALIZING_ES
    + _packs.OVER_VALIDATION_EN
    + _packs.OVER_VALIDATION_ES
    + INSULT_ANTI_PATTERN_PATTERNS
)

CLARIFICATION_DUMP_PATTERNS = _packs.CLARIFICATION_DUMP_ES

# ============================================================
# Reinforcement strings (Insult-specific — persona voice matters)
# ============================================================

CHARACTER_REINFORCEMENT = INSULT_REINFORCEMENT
CONTEXT_REINFORCEMENT = INSULT_CONTEXT_REINFORCEMENT
IDENTITY_REINFORCEMENT_SUFFIX = INSULT_IDENTITY_REINFORCEMENT_SUFFIX

# ============================================================
# Constants
# ============================================================

IDENTITY_REINFORCE_THRESHOLD = 10

# Marker separating cacheable (stable) prompt content from dynamic content.
# Everything BEFORE this marker is marked cache_control=ephemeral so Anthropic caches it.
# Everything AFTER is dynamic (time, preset, flows, facts) and changes per request.
# llm._send detects this marker to build a two-block system prompt.
CACHE_BOUNDARY = "\n<<<CACHE_BOUNDARY>>>\n"

# ============================================================
# Detection functions — wrap fi_core.persona detectors with composed patterns
# ============================================================

_break_detector = _BreakDetector(
    patterns=CHARACTER_BREAK_PATTERNS,
    reinforcement=CHARACTER_REINFORCEMENT,
)
_anti_monitor = _AntiPatternMonitor(patterns=ANTI_PATTERN_CHECKS)
_clarification_detector = _ClarificationDumpDetector(
    patterns=CLARIFICATION_DUMP_PATTERNS,
    context_reinforcement=CONTEXT_REINFORCEMENT,
)


def detect_break(text: str) -> list[str]:
    """Returns list of matched break patterns found in text."""
    return _break_detector.detect(text)


def detect_anti_patterns(text: str) -> list[str]:
    """Returns list of anti-pattern matches found in text.

    These are softer violations than character breaks — they indicate
    drift toward generic assistant behavior rather than identity leaks.
    """
    return _anti_monitor.detect(text)


def detect_clarification_dump(text: str) -> list[str]:
    """Returns list of matched clarification-dump patterns found in text.

    An empty list means the response did NOT deflect the task back to the user.
    A non-empty list means at least one deflection pattern matched.
    """
    return _clarification_detector.detect(text)


def sanitize(text: str) -> str:
    """Remove sentences that contain character breaks as a last resort.

    Wraps ``fi_core.persona.sanitize`` with this module's composed
    ``CHARACTER_BREAK_PATTERNS`` so callsites can keep the parameter-less
    signature they already use.
    """
    return _sanitize(text, patterns=CHARACTER_BREAK_PATTERNS)
