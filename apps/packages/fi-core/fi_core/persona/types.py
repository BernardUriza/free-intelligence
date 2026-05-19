"""Value types for persona / character-integrity detection results.

Frozen dataclasses — these are values, never mutated in place. Callers
log them, branch on them, and discard them.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DetectionResult:
    """Outcome of running a detector against a candidate response.

    `matched_patterns` is the list of regex source strings (the `.pattern`
    attribute of each matched `re.Pattern`) so callers can log which
    rules fired without having to recompile or inspect the regex objects.

    `clean` is the convenience flag — `True` when nothing matched.

    `severity` is consumer-defined ("break", "soft_drift", "clarification_dump").
    The persona module fills it in based on which detector produced the
    result; downstream observability can route on it.
    """

    matched_patterns: list[str] = field(default_factory=list)
    severity: str = "unspecified"

    @property
    def clean(self) -> bool:
        return not self.matched_patterns
