"""Behavioral preset system — classifies conversation mode and provides prompt guidance.

Each preset defines: activation triggers, emotional tone, rhetorical style,
avoidance rules, and transition conditions. The classifier analyzes the last
few messages + user profile to select the most appropriate preset.

Presets are NOT rigid modes — they're behavioral guidance injected into the
system prompt so the LLM naturally adopts the right energy.

This used to be one ~840-line module; it's now a package split by concern:
- ``types``     — PresetMode / PresetModifier / PresetSelection
- ``patterns``  — the compiled regex trigger tables + has_channel_noun
- ``guidance``  — per-mode/modifier prompt text + the vulnerable overlay + build_preset_prompt
- ``classifier``— the rule-based classify_preset + its helpers

This barrel re-exports the public surface so ``from insult.core.presets import X``
keeps working unchanged for every caller.
"""

from insult.core.presets.classifier import classify_preset
from insult.core.presets.guidance import (
    MODIFIER_GUIDANCE,
    PRESET_GUIDANCE,
    build_preset_prompt,
    build_vulnerable_overlay_prompt,
    is_vulnerable_overlay_selection,
)
from insult.core.presets.patterns import has_channel_noun
from insult.core.presets.types import PresetMode, PresetModifier, PresetSelection

__all__ = [
    "MODIFIER_GUIDANCE",
    "PRESET_GUIDANCE",
    "PresetMode",
    "PresetModifier",
    "PresetSelection",
    "build_preset_prompt",
    "build_vulnerable_overlay_prompt",
    "classify_preset",
    "has_channel_noun",
    "is_vulnerable_overlay_selection",
]
