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
is a ReDoS handed to a stranger — so the factory takes no arguments and reads
the vetted packs from `prompts/drift-patterns.json`.

The detectors are VENDORED (`drift_detect.py`), not imported: fi-core is not on
PyPI, so an import would have made this guard answer 503 on the very box it was
built for. It did, for one afternoon.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..contract import GuardOutcome
from .detect import Detector, compiled, packs, sanitize


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

    def _on_clarification(self, matched: list[Any], *,
                          final: bool) -> GuardOutcome:
        meta = {"severity": "clarification_dump", "matched": matched}
        if final:
            return GuardOutcome(metadata=meta)
        return GuardOutcome(metadata=meta, retry=True,
                            reinforcement=self.context_reinforcement)

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
    """The registry factory — vetted packs from content, no wire input, no
    network, no optional dependency. Reads the patterns at call time, so a tone
    fix is an edit to a JSON file rather than a redeploy of the daemon."""
    p = packs()
    breaks = compiled("break")
    return AntiDriftGuard(
        break_detector=Detector(patterns=breaks, severity="break"),
        anti_monitor=Detector(patterns=compiled("soft"), severity="soft_drift"),
        clarification_detector=Detector(patterns=compiled("clarification"),
                                        severity="clarification_dump"),
        sanitize_fn=sanitize,
        break_patterns=breaks,
        reinforcement=p.get("reinforcement", ""),
        context_reinforcement=p.get("context_reinforcement", ""),
    )
