"""Preset types — the mode/modifier enums + the classifier result dataclass.

Neutral contracts: no dependencies beyond the stdlib, so host-facing code
(routing) and the preset package (patterns/guidance/classifier) can import the
vocabulary without cycles. Moved here from `insult.core.presets.types` during the
routing-contracts extraction; that module now re-exports from here for
backwards compatibility (enum identity preserved).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PresetMode(StrEnum):
    DEFAULT_ABRASIVE = "default_abrasive"
    PLAYFUL_ROAST = "playful_roast"
    INTELLECTUAL_PRESSURE = "intellectual_pressure"
    RELATIONAL_PROBE = "relational_probe"
    RESPECTFUL_SERIOUS = "respectful_serious"
    META_DEFLECTION = "meta_deflection"
    ARC = "arc"  # Adaptive Relational Critique


class PresetModifier(StrEnum):
    MEMORY_RECALL = "memory_recall"
    CONTEMPT = "contempt"
    ACTION_INTENT = "action_intent"  # User wants a server action (channel creation, etc.)
    # Phase 2.5 (v3.6.3): user articulated a cross-domain conceptual link
    # (apartheid ↔ speciesism, neoliberalism ↔ self-help, etc.) and the
    # right move is to LEARN before challenging. See synthesis_detector.py
    # for the trigger heuristic.
    MULTI_DOMAIN_SYNTHESIS = "multi_domain_synthesis"


@dataclass
class PresetSelection:
    """Result of the preset classifier."""

    mode: PresetMode
    modifiers: list[PresetModifier] = field(default_factory=list)
    confidence: float = 0.7  # 0.0-1.0, how sure we are about the mode
    reason: str = ""  # debug: why this mode was selected

    @property
    def display_label(self) -> str:
        """Telemetry-friendly label. Renames RESPECTFUL_SERIOUS to
        `crisis_presence` when the mode was reached via acute-crisis
        routing, so the safety floor is visible in logs instead of
        hidden under the everyday clinical-vocab preset name.

        Internally the guidance is still the same RESPECTFUL_SERIOUS
        block (presence, not performance) — only the telemetry label
        changes. Use this in every log call instead of `.mode.value`."""
        if self.reason.startswith("acute_crisis"):
            return "crisis_presence"
        return self.mode.value
