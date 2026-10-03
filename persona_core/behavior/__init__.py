"""Persona-agnostic behavior engine — presets, vulnerability, synthesis.

The 4-flow analyzer pipeline (`behavior/flows/`) was DELETED 2026-07-20: it
had zero live callers since the purga. Its type contracts survive in
`behavior/contracts/flows.py` (consumed by the model router).

Resurrected 2026-07-14 from the deleted `personas/insult/core/` (commit
2f8d9ad^) and modularized so EVERY persona consumes it: the engine reads the
USER's state (message patterns, accumulated facts, conversational moves) and
selects modes; each persona's VOICE for those modes is content under
`shared/personas/guidance/<persona_id>/` (see `behavior.content`).
"""

from persona_core.behavior.presets import (
    PresetMode,
    PresetModifier,
    PresetSelection,
    build_preset_prompt,
    build_vulnerable_overlay_prompt,
    classify_preset,
    is_vulnerable_overlay_selection,
)
from persona_core.behavior.vulnerability import (
    VULNERABLE_THRESHOLD,
    compute_vulnerability_score,
    crisis_band,
    crisis_verdict,
    is_vulnerable_user,
)

__all__ = [
    "VULNERABLE_THRESHOLD",
    "PresetMode",
    "PresetModifier",
    "PresetSelection",
    "build_preset_prompt",
    "build_vulnerable_overlay_prompt",
    "classify_preset",
    "compute_vulnerability_score",
    "crisis_band",
    "crisis_verdict",
    "is_vulnerable_overlay_selection",
    "is_vulnerable_user",
]
