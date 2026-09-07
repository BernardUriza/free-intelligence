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
- **No CLAUSE negation stripping.** The chronic axis reads extracted FACTS
  (affirmative statements by construction) and the acute axis reads chat
  messages, where clinical negation phrasing ("niega ideación…") does not
  occur. :func:`.urgency._strip_negations` remains available to a caller that
  feeds clinical notes instead. LOCAL negation — a person's own "no me quiero
  morir" — does occur in chat, and since 0.29.0 a group whose every match sits
  right after a local cue is reported as ``denied`` instead of ``matched``,
  the same rule the vocabulary matcher applies (:data:`.urgency._LOCAL_NEGATION_RE`).

And one addition of 0.29.0 (Alex's H2, discord-bot #55): **exclusions**. Text
that is not about the writer's own state — an idiom ("me muero de risa"), a
topic ("vi un documental sobre el suicidio"), someone else's act ("mi hermana
intentó suicidarse") — is cut out before any group is matched, and reported as
``excluded``. An exclusion that is ALSO one of the axis's groups (the exposure
groups on the chronic axis) still scores its own weight: the span is read as
that group and as nothing else.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .urgency import _LOCAL_NEGATION_RE, strip_exclusions


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
    #: Groups whose every match sat right after a local negation cue ("no me
    #: quiero morir"). Not scored — a weak signal for the consumer to log.
    denied: tuple[str, ...] = ()
    #: Exclusion groups that cut a span before matching (idiom, topic, someone
    #: else's act). Explains why a phrase that looks like a crisis did not score.
    excluded: tuple[str, ...] = ()

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
    #: Spans cut out before matching (see module docstring). A group listed
    #: here AND in ``groups`` scores itself on the span, and nothing else does.
    exclusions: tuple[SignalGroup, ...] = ()

    def score(self, texts: Iterable[str]) -> ScoredSignals:
        """Evaluate ``texts`` as one body of evidence. Each group contributes
        its weight at most once, no matter how many texts match it."""
        matched: dict[str, int] = {}
        denied: set[str] = set()
        excluded: set[str] = set()
        own = {g.name for g in self.groups}
        for text in texts:
            if not text:
                continue
            for group in self.exclusions:
                if group.name in own and group.name not in matched and group.pattern.search(text):
                    matched[group.name] = group.weight
            text, fired = strip_exclusions(text, self.exclusions)
            excluded.update(fired)
            for group in self.groups:
                if group.name in matched:
                    continue
                starts = [m.start() for m in group.pattern.finditer(text)]
                if not starts:
                    continue
                if any(not _LOCAL_NEGATION_RE.search(text[:i]) for i in starts):
                    matched[group.name] = group.weight
                else:
                    denied.add(group.name)
        denied -= set(matched)
        return ScoredSignals(score=sum(matched.values()),
                             matched=tuple(sorted(matched)), threshold=self.threshold,
                             denied=tuple(sorted(denied)), excluded=tuple(sorted(excluded)))

    def crosses(self, texts: Iterable[str]) -> bool:
        return self.score(texts).crosses

    def matched(self, texts: Iterable[str]) -> tuple[str, ...]:
        """The group names that fired — telemetry can explain WHY without
        dumping the subject's texts into a log."""
        return self.score(texts).matched
