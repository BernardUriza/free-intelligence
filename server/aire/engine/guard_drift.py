"""The `antidrift` guard — persona character-integrity, backed by fi-core.

Transformational: it may request a retry, and once retries are exhausted it
sanitizes rather than asking again. Three deterministic detectors, checked in
priority order:

- **break** — a hard identity leak ("as an AI language model"). Retry-worthy;
  on the final attempt the offending sentences are dropped and the turn ships.
- **clarification dump** — the model stalling with questions instead of
  answering. A SOFT retry: ask once, then send as-is (lazy, not broken).
- **soft drift** — assistant tone, moralizing, therapy-speak. Logged only; the
  remedy is telemetry, never a retry storm.

Ported from fi-runner's `antidrift_guard`. The difference: fi-runner let the
CALLER pass its own pattern packs, because a runner in another repo composed
them. AIRE's wire may not — a caller-supplied regex on an internet-open daemon
is a ReDoS handed to a stranger — so the factory takes no arguments and uses
fi-core's vetted bilingual packs.

The fi-core import is LAZY, inside the factory: fi-core is not on PyPI, so the
droplet carries no hard dependency. A turn that never names this guard never
touches it; one that does, without fi-core installed, fails loudly at build.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .contract import GuardOutcome


@dataclass
class AntiDriftGuard:
    """Persona character-integrity over one turn's text."""

    break_detector: Any
    anti_monitor: Any
    clarification_detector: Any
    sanitize_fn: Any
    break_patterns: list[re.Pattern[str]]
    reinforcement: str = ""
    context_reinforcement: str = ""
    name: str = "antidrift"

    def _on_break(self, matched: list[Any], text: str, *, final: bool) -> GuardOutcome:
        if final:
            return GuardOutcome(
                metadata={"severity": "break", "matched": matched, "sanitized": True},
                text_override=self.sanitize(text),
            )
        return GuardOutcome(
            metadata={"severity": "break", "matched": matched},
            retry=True,
            reinforcement=self.reinforcement,
        )

    def _on_clarification(self, matched: list[Any], *, final: bool) -> GuardOutcome:
        meta = {"severity": "clarification_dump", "matched": matched}
        if final:
            return GuardOutcome(metadata=meta)
        return GuardOutcome(metadata=meta, retry=True, reinforcement=self.context_reinforcement)

    def inspect(
        self, *, response_text: str, context: tuple[str, ...] = (), final: bool = False
    ) -> GuardOutcome:
        breaks = self.break_detector.detect(response_text)
        if breaks:
            return self._on_break(breaks, response_text, final=final)
        clar = self.clarification_detector.detect(response_text)
        if clar:
            return self._on_clarification(clar, final=final)
        soft = self.anti_monitor.detect(response_text)
        if soft:
            return GuardOutcome(metadata={"severity": "soft_drift", "matched": soft})
        return GuardOutcome()

    def sanitize(self, text: str) -> str:
        """Last-resort cleanup — drop the sentences carrying a break pattern.
        Only reached once a retry has already failed."""
        return self.sanitize_fn(text, patterns=self.break_patterns)


def build_antidrift() -> AntiDriftGuard:
    """The registry factory — fi-core's vetted bilingual packs, no wire input."""
    from fi_core.persona import (
        AntiPatternMonitor,
        BreakDetector,
        ClarificationDumpDetector,
        sanitize,
    )
    from fi_core.persona.packs import (
        CLARIFICATION_DUMP_ES,
        CONTEXT_REINFORCEMENT,
        DEFAULT_BILINGUAL,
        GENERIC_REINFORCEMENT,
        MARKDOWN_DRIFT,
    )

    breaks = list(DEFAULT_BILINGUAL)
    return AntiDriftGuard(
        break_detector=BreakDetector(patterns=breaks, reinforcement=GENERIC_REINFORCEMENT),
        anti_monitor=AntiPatternMonitor(patterns=list(MARKDOWN_DRIFT)),
        clarification_detector=ClarificationDumpDetector(
            patterns=list(CLARIFICATION_DUMP_ES),
            context_reinforcement=CONTEXT_REINFORCEMENT,
        ),
        sanitize_fn=sanitize,
        break_patterns=breaks,
        reinforcement=GENERIC_REINFORCEMENT,
        context_reinforcement=CONTEXT_REINFORCEMENT,
    )
