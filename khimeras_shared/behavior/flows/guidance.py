"""Flow prompt-guidance helpers.

All prose lives in ``shared/personas/guidance/<persona_id>/flows/flow_*.md``.
Editing those files is picked up on the next request without a restart
(mtime-cached loader). A persona with no content for a fragment contributes
an empty string — the engine's analysis still runs.

This module only contains the enum → prompt-name mapping helpers consumed
by ``flows/prompt.py``.
"""

from __future__ import annotations

from khimeras_shared.behavior.content import load_guidance
from khimeras_shared.behavior.flows.model.types import (
    ConversationPattern,
    EpistemicMove,
    ResponseShape,
    StyleFlavor,
)


def get_epistemic_guidance(move: EpistemicMove, persona_id: str) -> str:
    """Load the prompt fragment for an epistemic move. Returns '' for NONE."""
    if move == EpistemicMove.NONE:
        return ""
    return load_guidance(persona_id, "flows", f"flow_epistemic_{move.value}")


def get_pressure_guidance(level: int, persona_id: str) -> str:
    """Load the prompt fragment for a pressure level. Level 2 is intentionally empty."""
    if level == 2:
        return ""
    return load_guidance(persona_id, "flows", f"flow_pressure_{level}")


def get_shape_guidance(shape: ResponseShape, persona_id: str) -> str:
    return load_guidance(persona_id, "flows", f"flow_shape_{shape.value}")


def get_flavor_guidance(flavor: StyleFlavor, persona_id: str) -> str:
    return load_guidance(persona_id, "flows", f"flow_flavor_{flavor.value}")


def get_awareness_tactics(pattern: ConversationPattern, persona_id: str) -> str:
    """Load the tactics block for a conversation pattern. Returns '' for NONE."""
    if pattern == ConversationPattern.NONE:
        return ""
    return load_guidance(persona_id, "flows", f"flow_awareness_{pattern.value}")


def get_depth_pattern_guidance(persona_id: str) -> str:
    return load_guidance(persona_id, "flows", "flow_depth_pattern")
