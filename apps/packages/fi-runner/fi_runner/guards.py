"""Guards — deterministic safety nets fi_runner runs in-process, backed by fi-core.

A **capability** is OPTIONAL: it exposes fi-core primitives as MCP tools the LLM
*may* call. A **guard** is a GUARANTEE: it runs on every turn, in-process, with no
LLM discretion. Deterministic fi-core safety nets belong here — a triage that must
escalate "plan suicida" → CRITICAL regardless of the model's phrasing, or an
anti-drift check that must sanitize an identity leak before it ships.

This is the seam that lets a runner stop importing fi-core directly: the guard
imports fi-core (lazily), the runner just declares the guard. fi_runner becomes
the single boundary to fi-core.

Two flavors, both satisfying the :class:`Guard` protocol:

- **observational** (``triage_guard``) — inspects the turn, returns findings in
  ``metadata``, never edits the text.
- **transformational** (``antidrift_guard``) — may request a ``retry`` (with a
  ``reinforcement`` string for the system prompt) and exposes ``sanitize()`` for
  last-resort cleanup once a retry has already failed.

``Runner(guards=[...])`` runs them after the turn and collects their outcomes on
``TurnResult.guard_outcomes``. A consumer with its own turn loop (e.g. insult's
multi-model retry client) can instead call a guard directly — same object, used
loose. Either way the runner no longer touches fi-core.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class GuardOutcome:
    """The result of running one guard over a turn.

    ``metadata`` carries observational findings (e.g. triage level, matched
    patterns). ``text_override`` replaces the response text (sanitize). ``retry``
    signals the caller should re-run the turn with ``reinforcement`` appended to
    the system prompt — fi_runner does NOT auto-retry (a consumer's loop owns the
    retry policy, which may be multi-model); the guard only detects and advises.
    """

    metadata: dict[str, Any] = field(default_factory=dict)
    text_override: str | None = None
    retry: bool = False
    reinforcement: str = ""

    @property
    def clean(self) -> bool:
        """True when the guard found nothing actionable (no edit, no retry)."""
        return self.text_override is None and not self.retry


@runtime_checkable
class Guard(Protocol):
    """A deterministic safety net fi_runner runs in-process every turn."""

    name: str

    def inspect(
        self, *, response_text: str, context: tuple[str, ...] = (), final: bool = False
    ) -> GuardOutcome:
        """Inspect a turn's ``response_text`` (plus optional ``context`` strings,
        e.g. the user's own messages) and return a :class:`GuardOutcome`.

        ``final`` is True on the last allowed attempt (retries exhausted): a
        transformational guard should stop requesting a retry and instead clean
        up (e.g. sanitize) so the pipeline can ship a best-effort result."""
        ...


# ---------------------------------------------------------------------------
# Observational: clinical urgency triage (fi_core.cognitive)
# ---------------------------------------------------------------------------


@dataclass
class TriageGuard:
    """Observational guard — deterministic clinical urgency triage.

    Wraps a :class:`fi_core.cognitive.UrgencyClassifier` for one domain. It NEVER
    edits the response; it classifies (response + the patient's own words) and
    reports the gravity score in ``metadata`` so the caller can escalate. Build
    via :func:`triage_guard` (which selects the domain and imports fi-core).
    """

    classifier: Any  # fi_core.cognitive.UrgencyClassifier
    patient_context: Any  # fi_core.cognitive.PatientContext (the class)
    name: str = "triage"

    def inspect(
        self, *, response_text: str, context: tuple[str, ...] = (), final: bool = False
    ) -> GuardOutcome:
        # `final` is irrelevant to an observational guard — it never retries.
        score = self.classifier.classify(
            self.patient_context(symptoms=[response_text, *context])
        )
        return GuardOutcome(
            metadata={
                "score": score,  # the typed GravityScore, for callers that want it
                "level": score.level.value,
                "gravity": score.final_gravity,
                "critical": score.critical_override,
                "reasons": list(score.reasons),
            }
        )


def triage_guard(domain: str = "psychiatry", *, name: str = "triage") -> TriageGuard:
    """Build a :class:`TriageGuard` for a clinical ``domain`` ("psychiatry", "cardiology")."""
    from fi_core.cognitive import DOMAINS, PatientContext

    dom = DOMAINS.get(domain)
    if dom is None:
        raise KeyError(f"unknown clinical domain {domain!r}; known: {sorted(DOMAINS)}")
    return TriageGuard(classifier=dom.urgency_classifier(), patient_context=PatientContext, name=name)


# ---------------------------------------------------------------------------
# Transformational: persona anti-drift (fi_core.persona)
# ---------------------------------------------------------------------------


@dataclass
class AntiDriftGuard:
    """Transformational guard — persona character-integrity (fi_core.persona).

    Detects, in priority order, a hard identity break, a clarification dump, or
    soft tone drift, using the three deterministic detectors. ``inspect`` returns:

    - break       → ``retry=True`` with ``reinforcement`` (hard, retry-worthy).
    - clarification→ ``retry=True`` with ``context_reinforcement`` (soft cue).
    - soft drift  → metadata only, no retry (log, don't retry-storm).

    fi_runner does not auto-retry; a consumer with a turn loop uses the outcome to
    re-run, then calls :meth:`sanitize` if the retry still breaks. Build via
    :func:`antidrift_guard`.
    """

    break_detector: Any  # fi_core.persona.BreakDetector
    anti_monitor: Any  # fi_core.persona.AntiPatternMonitor
    clarification_detector: Any  # fi_core.persona.ClarificationDumpDetector
    sanitize_fn: Any  # fi_core.persona.sanitize
    break_patterns: list[re.Pattern[str]]
    reinforcement: str = ""
    context_reinforcement: str = ""
    name: str = "antidrift"

    def inspect(
        self, *, response_text: str, context: tuple[str, ...] = (), final: bool = False
    ) -> GuardOutcome:
        breaks = self.break_detector.detect(response_text)
        if breaks:
            if final:
                # Retries exhausted — last-resort cleanup: drop the offending
                # sentences and ship, rather than retry again.
                return GuardOutcome(
                    metadata={"severity": "break", "matched": breaks, "sanitized": True},
                    text_override=self.sanitize(response_text),
                )
            return GuardOutcome(
                metadata={"severity": "break", "matched": breaks},
                retry=True,
                reinforcement=self.reinforcement,
            )
        clar = self.clarification_detector.detect(response_text)
        if clar:
            # Clarification dump is a SOFT retry: ask once, but on the final
            # attempt send as-is (the bot is lazy, not character-broken).
            if final:
                return GuardOutcome(metadata={"severity": "clarification_dump", "matched": clar})
            return GuardOutcome(
                metadata={"severity": "clarification_dump", "matched": clar},
                retry=True,
                reinforcement=self.context_reinforcement,
            )
        soft = self.anti_monitor.detect(response_text)
        if soft:
            # Soft drift is logged, never retried — the right remedy is telemetry.
            return GuardOutcome(metadata={"severity": "soft_drift", "matched": soft})
        return GuardOutcome()  # clean

    def sanitize(self, text: str) -> str:
        """Last-resort cleanup — drop sentences with break patterns. Only call
        AFTER a retry has already failed (mirrors fi_core.persona.sanitize)."""
        return self.sanitize_fn(text, patterns=self.break_patterns)


def antidrift_guard(
    *,
    break_patterns: list[re.Pattern[str]],
    soft_patterns: list[re.Pattern[str]] | None = None,
    clarification_patterns: list[re.Pattern[str]] | None = None,
    reinforcement: str = "",
    context_reinforcement: str = "",
    name: str = "antidrift",
) -> AntiDriftGuard:
    """Build an :class:`AntiDriftGuard` from a runner's composed pattern packs.

    The runner supplies its full pattern lists (compose fi-core's built-in packs —
    re-exported as :mod:`fi_runner.packs` — with its own patterns). The guard
    imports the fi-core detectors; the runner does not import fi-core.
    """
    from fi_core.persona import (
        AntiPatternMonitor,
        BreakDetector,
        ClarificationDumpDetector,
        sanitize,
    )

    breaks = list(break_patterns)
    return AntiDriftGuard(
        break_detector=BreakDetector(patterns=breaks, reinforcement=reinforcement),
        anti_monitor=AntiPatternMonitor(patterns=list(soft_patterns or [])),
        clarification_detector=ClarificationDumpDetector(
            patterns=list(clarification_patterns or []),
            context_reinforcement=context_reinforcement,
        ),
        sanitize_fn=sanitize,
        break_patterns=breaks,
        reinforcement=reinforcement,
        context_reinforcement=context_reinforcement,
        name=name,
    )


__all__ = [
    "Guard",
    "GuardOutcome",
    "TriageGuard",
    "AntiDriftGuard",
    "triage_guard",
    "antidrift_guard",
]
