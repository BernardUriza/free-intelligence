"""Preset prompt guidance — builds the behavioral section of the system prompt.

The ENGINE (mode selection) is persona-agnostic; the PROSE is each persona's
voice, living in ``shared/personas/guidance/<persona_id>/presets/*.md``
(``preset_guidance_*``, ``preset_modifier_*``, ``preset_intentionality_directive``,
``preset_vulnerable_overlay``). Editing any of those files is picked up on the
next request without a restart. A persona with no content contributes nothing —
the engine still classifies, the prompt just carries no voice-specific block.

The ONE exception is ``preset_vulnerable_overlay``: its safety floor lives in
the shared ``_base`` guidance id and EVERY persona inherits it, so an absent
file there means "no tone of my own", never "no safety floor".
"""

from __future__ import annotations

from persona_core.behavior.content import load_guidance
from persona_core.behavior.presets.types import PresetSelection

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


# The safety floor lives ONCE, under the reserved ``_base`` guidance id, and
# every persona inherits it. A persona's own overlay file carries ONLY its
# tone. The merge is asymmetric ON PURPOSE: base first, persona voice after,
# and the persona layer may ADD, never subtract. If each persona brought its
# own floor there would be no floor — five different answers to what to do
# with someone fragile. See #44.
BASE_GUIDANCE_ID = "_base"


def build_vulnerable_overlay_prompt(persona_id: str) -> str:
    """Return the safety overlay text appended when a user is vulnerable.

    Shared safety floor first, persona tone second. Every persona receives the
    floor even when it has written no overlay of its own: an absent file is a
    missing TONE, never a missing safety floor.
    """
    base = load_guidance(BASE_GUIDANCE_ID, "presets", "preset_vulnerable_overlay")
    voice = "" if persona_id == BASE_GUIDANCE_ID else load_guidance(persona_id, "presets", "preset_vulnerable_overlay")
    return "\n" + "\n\n".join(part for part in (base, voice) if part)


# ---------------------------------------------------------------------------
# Preset prompt builder
# ---------------------------------------------------------------------------


def build_preset_prompt(selection: PresetSelection, persona_id: str) -> str:
    """Build the preset guidance section for injection into system prompt.

    Layer order: INTENTIONALITY (strategic, why-do-I-move) → PRESET
    (tactical, how-do-I-move) → MODIFIERS (overlays).

    All prose is loaded from the persona's guidance dir at call time
    (mtime-cached), so editing a .md file is picked up on the next request
    without a restart.
    """
    intentionality = load_guidance(persona_id, "presets", "preset_intentionality_directive")
    preset_text = load_guidance(persona_id, "presets", f"preset_guidance_{selection.mode.value}")
    parts = [p for p in (intentionality, preset_text) if p]
    for modifier in selection.modifiers:
        guidance = load_guidance(persona_id, "presets", f"preset_modifier_{modifier.value}")
        if guidance:
            parts.append(guidance)
    return "\n\n".join(parts)
