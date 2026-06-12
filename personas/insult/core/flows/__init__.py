"""Behavioral flow analysis — 4-flow pre-generation pipeline.

What used to be a 1165-line monolith (`insult/core/flows.py`) is now a
package with clear separation of concerns:

- `types.py`        Enums + dataclasses (the vocabulary)
- `patterns.py`     All regex patterns, shared across analyzers
- `guidance.py`     Static prompt templates (shape/flavor/pressure text)
- `history.py`      ExpressionHistory — anti-repetition tracking
- `analyzers/`      One analyzer per flow, implementing the Analyzer Protocol
- `pipeline.py`     FlowPipeline — orchestrator with cross-flow overrides
- `prompt.py`       build_flow_prompt — renders the FlowAnalysis to markdown
- `validator.py`    validate_flow_adherence — post-generation compliance check

External callers should import from this package as before
(`from personas.insult.core.flows import analyze_flows, FlowAnalysis`). The
flat imports preserve backwards compatibility so the chat cog and the
character guard don't need to know about the internal structure.

## Adding a new flow

1. Define any new enums/dataclasses in `types.py`.
2. Add regex patterns in `patterns.py`.
3. Add prompt guidance in `guidance.py`.
4. Create a new `analyzers/<name>.py` implementing `Analyzer`.
5. Append the class to `pipeline.DEFAULT_ANALYZERS`.
6. Teach `build_flow_prompt` to render the new block (if wanted).

No pipeline rewiring needed — the Protocol makes new analyzers plug-and-play.

## Why this structure (and not a standalone PyPI package)

The vocabulary (ecphrastic/reflexive flavors, DEFAULT_ABRASIVE preset
coupling, specific pressure escalation rules) is opinionated to
Insult's persona. Nothing here would be useful to another bot without
heavy surgery. Keeping it as a subpackage respects the monorepo
principle: tight coupling + single release cycle = stay together. See
the 2026-04-24 /histerical-search investigation for the sources and
full rationale.
"""

from personas.insult.core.flows.analyzers import (
    Analyzer,
    AwarenessAnalyzer,
    EpistemicAnalyzer,
    ExpressionAnalyzer,
    FlowContext,
    PressureAnalyzer,
)
from personas.insult.core.flows.history import EXPRESSION_HISTORY_MAXLEN, ExpressionHistory
from personas.insult.core.flows.pipeline import DEFAULT_ANALYZERS, FlowPipeline, analyze_flows
from personas.insult.core.flows.prompt import build_flow_prompt
from personas.insult.core.flows.types import (
    AwarenessAnalysis,
    ConversationPattern,
    EpistemicAnalysis,
    EpistemicMove,
    ExpressionAnalysis,
    FlowAnalysis,
    PressureAnalysis,
    ResponseShape,
    StyleFlavor,
    UserState,
)
from personas.insult.core.flows.validator import detect_lifelessness, validate_flow_adherence


# ─── Backwards-compatible function aliases ─────────────────────────────────
#
# The pre-refactor module exposed private functions (`_analyze_epistemic`,
# `_detect_contradiction`, `_select_shape`, ...) that tests depend on.
# These are now methods on the Analyzer classes. To keep the test suite
# green without a sweeping rewrite, we re-export thin wrappers that
# preserve the original call signatures. New tests should import the
# Analyzer classes directly.
def _analyze_epistemic(current_message: str, user_messages: list[str]) -> EpistemicAnalysis:
    return EpistemicAnalyzer()._score(current_message, user_messages)


def _detect_contradiction(current: str, prior_messages: list[str]) -> bool:
    return EpistemicAnalyzer._detect_contradiction(current, prior_messages)


def _analyze_pressure(
    current_message: str,
    recent_messages: list[dict],
    preset,
) -> PressureAnalysis:
    return PressureAnalyzer()._score(current_message, recent_messages, preset)


def _analyze_awareness(current_message: str, recent_messages: list[dict]) -> AwarenessAnalysis:
    return AwarenessAnalyzer()._score(current_message, recent_messages)


def _detect_repetition_loop(user_messages: list[str]) -> tuple[bool, int]:
    return AwarenessAnalyzer._detect_repetition_loop(user_messages)


def _select_shape(
    current_message: str,
    preset,
    pressure: PressureAnalysis,
    epistemic: EpistemicAnalysis,
    recent_shapes: list[str],
) -> tuple[ResponseShape, str, list[str]]:
    return ExpressionAnalyzer._select_shape(current_message, preset, pressure, epistemic, recent_shapes)


def _select_flavor(
    current_message: str,
    preset,
    pressure: PressureAnalysis,
    recent_flavors: list[str],
) -> tuple[StyleFlavor, str, list[str]]:
    return ExpressionAnalyzer._select_flavor(current_message, preset, pressure, recent_flavors)


__all__ = [
    "DEFAULT_ANALYZERS",
    "EXPRESSION_HISTORY_MAXLEN",
    "Analyzer",
    "AwarenessAnalysis",
    "AwarenessAnalyzer",
    "ConversationPattern",
    "EpistemicAnalysis",
    "EpistemicAnalyzer",
    "EpistemicMove",
    "ExpressionAnalysis",
    "ExpressionAnalyzer",
    "ExpressionHistory",
    "FlowAnalysis",
    "FlowContext",
    "FlowPipeline",
    "PressureAnalysis",
    "PressureAnalyzer",
    "ResponseShape",
    "StyleFlavor",
    "UserState",
    "analyze_flows",
    "build_flow_prompt",
    "detect_lifelessness",
    "validate_flow_adherence",
]
