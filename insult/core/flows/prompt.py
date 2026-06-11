"""Convert a FlowAnalysis into the prompt fragment for system injection.

Pure function — takes the structured analysis and emits markdown text
blocks per active flow. Kept separate from the analyzers so prompt
tuning doesn't require touching logic code."""

from __future__ import annotations

from insult.core.flows.guidance import (
    get_awareness_tactics,
    get_depth_pattern_guidance,
    get_epistemic_guidance,
    get_flavor_guidance,
    get_pressure_guidance,
    get_shape_guidance,
)
from insult.core.flows.types import (
    ConversationPattern,
    FlowAnalysis,
    UserState,
)

# States that trigger the depth-pattern rider. Pressure >= 4 also triggers.
_DEPTH_TRIGGER_STATES = frozenset({UserState.SINCERE, UserState.VULNERABLE})


def build_flow_prompt(analysis: FlowAnalysis) -> str:
    """Render the flow plan as a markdown prompt fragment.

    Structure: epistemic block → pressure block (if not baseline) →
    depth rider (if earned) → expression preamble + shape + flavor →
    awareness block (if pattern detected). Empty sections are skipped
    so the prompt never contains dead headers.
    """
    parts: list[str] = []

    # -- Epistemic --
    guidance = get_epistemic_guidance(analysis.epistemic.recommended_move)
    if guidance:
        parts.append(guidance)

    # -- Pressure (baseline level 2 intentionally empty) --
    pressure_text = get_pressure_guidance(analysis.pressure.pressure_level)
    if pressure_text:
        parts.append(pressure_text)

    # -- Depth rider: when the user brings weight, bare validation is
    # unacceptable. Triggers on sincere/vulnerable OR pressure >= 4.
    # DEFAULT / PLAYFUL stay unaffected — a "Nel." to "me llevo mi mac?"
    # is perfect there.
    if analysis.pressure.detected_state in _DEPTH_TRIGGER_STATES or analysis.pressure.pressure_level >= 4:
        parts.append(get_depth_pattern_guidance())

    # -- Expression (always — but framed as hard constraint). Shape and
    # flavor are the most-enforced part of the flow prompt because
    # they're the most-violated in practice.
    parts.append(
        "## Response Expression (MANDATORY — override verbosity impulse)\n"
        "The shape below is a HARD CONSTRAINT on your response structure. "
        "Follow it even if the input tempts you to say more."
    )
    parts.append(get_shape_guidance(analysis.expression.selected_shape))
    parts.append(get_flavor_guidance(analysis.expression.selected_flavor))

    # -- Awareness (only when a meta-pattern was actually detected) --
    if analysis.awareness.detected_pattern != ConversationPattern.NONE:
        awareness_parts = [
            f"## Conversational Awareness: {analysis.awareness.detected_pattern.value.replace('_', ' ').title()}"
        ]
        if analysis.awareness.meta_commentary:
            awareness_parts.append(f"Consider dropping this meta-observation: '{analysis.awareness.meta_commentary}'")
        if analysis.awareness.delayed_question:
            awareness_parts.append(f"Powerful delayed question to deploy: '{analysis.awareness.delayed_question}'")
        awareness_parts.append(get_awareness_tactics(analysis.awareness.detected_pattern))
        parts.append("\n".join(awareness_parts))

    return "\n\n".join(parts)
