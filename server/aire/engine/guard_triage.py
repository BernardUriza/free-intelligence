"""The `triage` guard — deterministic clinical urgency, backed by fi-core.

Observational: it NEVER edits the response. It classifies the turn (the model's
text plus the user's own words) and reports the gravity score in `metadata`, so
a consumer can escalate. `guard_exec` turns a CRITICAL outcome into a
`guard_critical` event — that is the whole point of an observational guard: a
signal that must reach a human even though nothing was rewritten.

Ported from fi-runner's `triage_guard`. Two deliberate narrowings for AIRE:
the wire cannot choose the clinical domain (it is not a caller's decision on a
shared daemon), and the fi-core import is LAZY inside the factory.

Its backing — `fi_core.cognitive`'s Python — had no application consumer at the
2026-08-22 audit: only fi-runner's own tests, examples and benchmarks reached
it, and no app ever requested `capabilities=["cognitive"]`. It is ported to
preserve the work, not because a caller exists. If `fi_core.cognitive`'s Python
is ever dropped, this file goes with it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contract import GuardOutcome

DEFAULT_DOMAIN = "psychiatry"


@dataclass
class TriageGuard:
    """Deterministic clinical urgency triage over one turn's text."""

    classifier: Any
    patient_context: Any
    name: str = "triage"

    def inspect(
        self, *, response_text: str, context: tuple[str, ...] = (), final: bool = False
    ) -> GuardOutcome:
        score = self.classifier.classify(
            self.patient_context(symptoms=[response_text, *context])
        )
        return GuardOutcome(
            metadata={
                "score": score,
                "level": score.level.value,
                "gravity": score.final_gravity,
                "critical": score.critical_override,
                "reasons": list(score.reasons),
            }
        )


def build_triage(domain: str = DEFAULT_DOMAIN) -> TriageGuard:
    """The registry factory. `domain` is a server-side argument, not a wire field."""
    from fi_core.cognitive import DOMAINS, PatientContext

    dom = DOMAINS.get(domain)
    if dom is None:
        raise KeyError(f"unknown clinical domain {domain!r}; known: {sorted(DOMAINS)}")
    return TriageGuard(classifier=dom.urgency_classifier(), patient_context=PatientContext)
