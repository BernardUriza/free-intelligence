"""Detectors for character breaks, soft drift, and clarification dumps.

Three detector classes — one per failure mode — plus a `sanitize` helper
for last-resort cleanup. All deterministic regex matching; zero LLM calls
at detection time.

Failure mode → remedy mapping:

    BreakDetector                 hard identity leak  → retry w/ reinforcement
    AntiPatternMonitor            soft drift (tone)   → log only, don't block
    ClarificationDumpDetector     bot punting task    → retry w/ context cue

Typical use:

    from fi_core.persona import BreakDetector, packs, sanitize

    detector = BreakDetector(
        patterns=packs.GENERIC_AI_DISCLOSURE_EN + packs.GENERIC_AI_DISCLOSURE_ES,
        reinforcement=packs.GENERIC_REINFORCEMENT,
    )

    matches = detector.detect(llm_response)
    if matches:
        new_response = llm.retry(system_prompt + detector.reinforcement)
        if detector.detect(new_response):
            new_response = sanitize(new_response, patterns=detector.patterns)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from fi_core.persona.types import DetectionResult


@dataclass
class BreakDetector:
    """Detects hard identity-leak patterns ("I'm an AI", "as a language model").

    Intended for blocking retries: when `detect()` returns non-empty, the
    caller should retry the LLM call with `reinforcement` appended to the
    system prompt. If the retry also matches, fall back to `sanitize()`.

    Patterns and reinforcement are deliberately separate so callers can
    log "what broke" independently of "what we told the model to do
    about it."
    """

    patterns: list[re.Pattern[str]]
    reinforcement: str = ""

    def detect(self, text: str) -> list[str]:
        """Return list of matched pattern source strings.

        Empty list means the response is clean (no break detected).
        Non-empty list contains the `.pattern` attribute of each
        `re.Pattern` that matched — suitable for logging or alerting.
        """
        return [p.pattern for p in self.patterns if p.search(text)]

    def check(self, text: str) -> DetectionResult:
        """Same as `detect`, but returns a `DetectionResult` with severity."""
        return DetectionResult(
            matched_patterns=self.detect(text),
            severity="break",
        )


@dataclass
class AntiPatternMonitor:
    """Detects soft drift toward generic-assistant tone.

    Unlike `BreakDetector`, these violations are logged for monitoring
    but DO NOT block the response. A bot saying "great question!" is
    annoying, not character-broken — the right remedy is telemetry,
    not retry-storm.
    """

    patterns: list[re.Pattern[str]]

    def detect(self, text: str) -> list[str]:
        """Return list of matched anti-pattern source strings.

        Empty list = no anti-pattern detected.
        Non-empty list = matched patterns. Suggested usage: emit one
        telemetry event per match.
        """
        return [p.pattern for p in self.patterns if p.search(text)]

    def check(self, text: str) -> DetectionResult:
        """Same as `detect`, but returns a `DetectionResult` with severity."""
        return DetectionResult(
            matched_patterns=self.detect(text),
            severity="soft_drift",
        )


@dataclass
class ClarificationDumpDetector:
    """Detects responses that punt the task back to the user.

    Example: user says "Es solo una búsqueda sencilla. Hazla." and the
    bot replies "Dime qué busco." despite having context. The remedy is
    to retry with `context_reinforcement` appended — pointing the model
    to use the conversation context it already has.

    Distinct from `BreakDetector` because the failure mode is different:
    the bot is not out of character, it is being lazy.
    """

    patterns: list[re.Pattern[str]]
    context_reinforcement: str = ""

    def detect(self, text: str) -> list[str]:
        """Return list of matched clarification-dump source strings.

        Empty list = no dump detected.
        Non-empty list = matched patterns.
        """
        return [p.pattern for p in self.patterns if p.search(text)]

    def check(self, text: str) -> DetectionResult:
        """Same as `detect`, but returns a `DetectionResult` with severity."""
        return DetectionResult(
            matched_patterns=self.detect(text),
            severity="clarification_dump",
        )


def sanitize(text: str, patterns: list[re.Pattern[str]]) -> str:
    """Remove sentences containing pattern matches as last-resort cleanup.

    Splits `text` on sentence-ending punctuation, drops every sentence
    that contains a match for any pattern in `patterns`, joins what's
    left. If sanitization would remove everything (all sentences match),
    returns the original `text` rather than empty string — let the
    caller decide whether to drop or send-anyway.

    Not a retry replacement — only invoke after a retry has already
    failed.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    clean = [s for s in sentences if not any(p.search(s) for p in patterns)]
    result = " ".join(clean).strip()
    return result if result else text
