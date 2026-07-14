"""Persona-agnostic behavior engine — presets, flows, vulnerability, synthesis.

Resurrected 2026-07-14 from the deleted `personas/insult/core/` (commit
2f8d9ad^) and modularized so EVERY persona consumes it: the engine reads the
USER's state (message patterns, accumulated facts, conversational moves) and
selects modes; each persona's VOICE for those modes is content under
`shared/personas/guidance/<persona_id>/` (see `behavior.content`).
"""

from khimeras_shared.behavior.presets import (
    PresetMode,
    PresetModifier,
    PresetSelection,
    build_preset_prompt,
    build_vulnerable_overlay_prompt,
    classify_preset,
    is_vulnerable_overlay_selection,
)
from khimeras_shared.behavior.vulnerability import (
    VULNERABLE_THRESHOLD,
    compute_vulnerability_score,
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
    "is_vulnerable_overlay_selection",
    "is_vulnerable_user",
]
