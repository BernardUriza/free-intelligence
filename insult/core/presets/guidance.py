"""Preset prompt guidance — builds the behavioral section of the system prompt.

All prose lives in ``insult/prompts/preset_guidance_*.md``,
``insult/prompts/preset_modifier_*.md``,
``insult/prompts/preset_intentionality_directive.md``, and
``insult/prompts/preset_vulnerable_overlay.md``.
Editing any of those files is picked up on the next request without a restart.
"""

from __future__ import annotations

from insult.core.presets.types import PresetModifier, PresetSelection
from insult.core.prompts_loader import load_prompt

# ---------------------------------------------------------------------------
# Vulnerable-user overlay routing helpers
# ---------------------------------------------------------------------------

# Reason prefixes that activate the chronic-care / acute-crisis safety
# overlay downstream. Kept as a tuple so a future routing reason can be
# added in one place without touching callers.
_OVERLAY_REASON_PREFIXES: tuple[str, ...] = (
    # Legacy: pre-F1 chronic-vulnerable forcing RESPECTFUL_SERIOUS. No longer
    # emitted but kept here so any in-flight selection still picks up overlay.
    "vulnerable_user_overlay",
    # F1: chronic-vulnerable + non-acute current message — routes to a
    # movement-permitting preset under a sharpness cap (no longer flat).
    "chronic_nonacute_move_allowed",
    # F1: chronic-vulnerable user whose CURRENT message contains clinical
    # vocabulary (e.g. Alex asking about quetiapine). Routes to
    # RESPECTFUL_SERIOUS via priority 1 BUT still activates the overlay so
    # the clinical-source allowlist + dosing discipline apply — the
    # exact moment that safety matters most.
    "chronic_serious_clinical_current",
    # F1: acute distress in the current message — strongest safety floor.
    "acute_crisis",
)


def is_vulnerable_overlay_selection(selection: PresetSelection) -> bool:
    """True if the PresetSelection should receive the chronic-care safety
    overlay (no abrasive tone, clinical-source discipline, crisis hotlines
    only on acute distress, sharpness cap, etc.).

    The reason prefix is the canonical marker — adding a new reason that
    needs the overlay only requires extending _OVERLAY_REASON_PREFIXES."""
    return selection.reason.startswith(_OVERLAY_REASON_PREFIXES)


def build_vulnerable_overlay_prompt() -> str:
    """Return the safety overlay text appended when a user is vulnerable."""
    return "\n" + load_prompt("preset_vulnerable_overlay")


# ---------------------------------------------------------------------------
# Preset prompt builder
# ---------------------------------------------------------------------------


def build_preset_prompt(selection: PresetSelection) -> str:
    """Build the preset guidance section for injection into system prompt.

    Layer order: INTENTIONALITY (strategic, why-do-I-move) → PRESET
    (tactical, how-do-I-move) → MODIFIERS (overlays).

    All prose is loaded from insult/prompts/*.md at call time (mtime-cached),
    so editing a .md file is picked up on the next request without a restart.
    """
    intentionality = load_prompt("preset_intentionality_directive")
    preset_text = load_prompt(f"preset_guidance_{selection.mode.value}")
    parts = [intentionality, preset_text]
    for modifier in selection.modifiers:
        if modifier == PresetModifier.ACTION_INTENT:
            # No behavioral guidance — chat.py forces tool_choice instead.
            continue
        guidance = load_prompt(f"preset_modifier_{modifier.value}")
        if guidance:
            parts.append(guidance)
    return "\n\n".join(parts)
