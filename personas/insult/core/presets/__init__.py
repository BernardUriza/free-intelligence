"""Behavioral preset system — classifies conversation mode and provides prompt guidance.

Each preset defines: activation triggers, emotional tone, rhetorical style,
avoidance rules, and transition conditions. The classifier analyzes the last
few messages + user profile to select the most appropriate preset.

Presets are NOT rigid modes — they're behavioral guidance injected into the
system prompt so the LLM naturally adopts the right energy.

This used to be one ~840-line module; it's now a package split by concern:
- ``types``     — PresetMode / PresetModifier / PresetSelection
- ``patterns``  — the compiled regex trigger tables
- ``guidance``  — per-mode/modifier prompt text + the vulnerable overlay + build_preset_prompt
- ``classifier``— the rule-based classify_preset + its helpers

This barrel re-exports the public surface so ``from personas.insult.core.presets import X``
keeps working unchanged for every caller.
"""

from personas.insult.core.presets.classifier import classify_preset
from personas.insult.core.presets.guidance import (
    build_preset_prompt,
    build_vulnerable_overlay_prompt,
    is_vulnerable_overlay_selection,
)
from personas.insult.core.presets.types import PresetMode, PresetModifier, PresetSelection

# Only the symbols callers actually import. PRESET_GUIDANCE / MODIFIER_GUIDANCE
# stay internal to the `guidance` module — no one imports them from the barrel.
__all__ = [
    "PresetMode",
    "PresetModifier",
    "PresetSelection",
    "build_preset_prompt",
    "build_vulnerable_overlay_prompt",
    "classify_preset",
    "is_vulnerable_overlay_selection",
]
