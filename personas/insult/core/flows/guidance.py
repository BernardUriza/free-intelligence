"""Flow prompt-guidance helpers.

All prose lives in ``insult/prompts/flow_*.md``. Editing those files is
picked up on the next request without a restart (mtime-cached loader).

This module only contains the enum → prompt-name mapping helpers consumed
by ``flows/prompt.py``.
"""

from __future__ import annotations

from personas.insult.core.flows.types import (
    ConversationPattern,
    EpistemicMove,
    ResponseShape,
    StyleFlavor,
)
from personas.insult.core.prompts_loader import load_prompt


def get_epistemic_guidance(move: EpistemicMove) -> str:
    """Load the prompt fragment for an epistemic move. Returns '' for NONE."""
    if move == EpistemicMove.NONE:
        return ""
    return load_prompt(f"flow_epistemic_{move.value}")


def get_pressure_guidance(level: int) -> str:
    """Load the prompt fragment for a pressure level. Level 2 is intentionally empty."""
    if level == 2:
        return ""
    try:
        return load_prompt(f"flow_pressure_{level}")
    except FileNotFoundError:
        return ""


def get_shape_guidance(shape: ResponseShape) -> str:
    return load_prompt(f"flow_shape_{shape.value}")


def get_flavor_guidance(flavor: StyleFlavor) -> str:
    return load_prompt(f"flow_flavor_{flavor.value}")


def get_awareness_tactics(pattern: ConversationPattern) -> str:
    """Load the tactics block for a conversation pattern. Returns '' for NONE."""
    if pattern == ConversationPattern.NONE:
        return ""
    return load_prompt(f"flow_awareness_{pattern.value}")


def get_depth_pattern_guidance() -> str:
    return load_prompt("flow_depth_pattern")
