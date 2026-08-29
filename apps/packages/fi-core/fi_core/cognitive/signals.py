"""Weighted signal groups — accumulated evidence, where flat sets can only count.

The flat-frozenset vocabularies in :mod:`.urgency` answer *"does this text name
a symptom?"*. They cannot answer *"do these texts, together, add up to enough?"*
— and that second question is how real vulnerability manifests: isolated
mentions are often metaphorical ("estoy traumado con el código"), while
CLUSTERS (a named diagnosis + its medication, a hospitalization + a clinician)
are load-bearing. discord-bot proved this in production for months with a
weighted corpus its repo had to keep OUTSIDE fi-core precisely because
``ClinicalDomain`` had nowhere to hold a weight or a regex. This module is
that missing shape, promoted into the framework (framework-first-canary:
Bernard, 2026-08-28 — "discord-bot solo debe usar el clinical domain").

Two deliberate parity decisions, inherited from the production corpus:

- **A group scores its weight AT MOST ONCE per evaluation.** Fact extractors
  emit 2-5 redundant facts per underlying event; counting each would let a
  single isolated signal cross a threshold built for clusters.
- **No negation stripping.** The chronic axis reads extracted FACTS
  (affirmative statements by construction) and the acute axis reads chat
  messages, where clinical negation phrasing ("niega ideación…") does not
  occur. :func:`.urgency._strip_negations` remains available to a caller that
  feeds clinical notes instead.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class SignalGroup:
    """One weighted family of patterns (a diagnosis cluster, a medication
    family, an explicit-ideation phrasing…).

    ``weight`` is clinical content, not engineering: values migrate verbatim
    from a validated corpus or are proposed explicitly for clinical review —
    never tuned casually. ``category`` ties the group to the domain vocabulary
    (e.g. a ``high_risk_conditions`` entry that previously had no detector).
    """

    name: str
    weight: int
    pattern: re.Pattern[str]
    category: str = "general"

    @staticmethod
    def make(name: str, weight: int, pattern: str, *, category: str = "general") -> "SignalGroup":
        """Compile ``pattern`` case-insensitively. The canonical constructor."""
        return SignalGroup(name=name, weight=weight,
                           pattern=re.compile(pattern, re.IGNORECASE), category=category)


@dataclass(frozen=True)
class ScoredSignals:
    """The outcome of one evaluation: the total and *why* (explainable, like
    :class:`.urgency.GravityScore` — never a bare number)."""

    score: int
    matched: tuple[str, ...]
    threshold: int

    @property
    def crosses(self) -> bool:
        return self.score >= self.threshold


@dataclass(frozen=True)
class WeightedSignals:
    """A weighted corpus for ONE axis of a clinical domain.

    A domain typically carries two, orthogonal by construction:

    - a CHRONIC axis evaluated over the subject's accumulated facts
      ("does the long-term record show a vulnerability cluster?"), and
    - an ACUTE axis evaluated over the current message
      ("is this person in distress RIGHT NOW?").

    The same engine serves both; only the texts fed in differ.
    """

    groups: tuple[SignalGroup, ...]
    threshold: int

    def score(self, texts: Iterable[str]) -> ScoredSignals:
        """Evaluate ``texts`` as one body of evidence. Each group contributes
        its weight at most once, no matter how many texts match it."""
        matched: dict[str, int] = {}
        for text in texts:
            if not text:
                continue
            for group in self.groups:
                if group.name not in matched and group.pattern.search(text):
                    matched[group.name] = group.weight
        return ScoredSignals(score=sum(matched.values()),
                             matched=tuple(sorted(matched)), threshold=self.threshold)

    def crosses(self, texts: Iterable[str]) -> bool:
        return self.score(texts).crosses

    def matched(self, texts: Iterable[str]) -> tuple[str, ...]:
        """The group names that fired — telemetry can explain WHY without
        dumping the subject's texts into a log."""
        return self.score(texts).matched
