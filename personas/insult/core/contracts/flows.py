"""Enums and dataclasses for the flow pipeline.

Neutral contracts: depends only on the stdlib so both host-facing code
(routing) and the smart flow analyzers can import the vocabulary without
pulling in regex patterns or analyzer implementations. Moved here from
`insult.core.flows.types` during the routing-contracts extraction; that module
now re-exports from here for backwards compatibility (enum identity preserved).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum

# ═══════════════════════════════════════════════════════════════════════════
# Enums — the vocabulary of the flow system
# ═══════════════════════════════════════════════════════════════════════════


class EpistemicMove(StrEnum):
    """How to engage with the user's truthfulness and argument quality."""

    COMPRESS = "compress"
    CHALLENGE_PREMISE = "challenge_premise"
    CONCEDE_PARTIAL = "concede_partial"
    CALL_CONTRADICTION = "call_contradiction"
    DEMAND_EVIDENCE = "demand_evidence"
    NONE = "none"


class UserState(StrEnum):
    """Classification of the user's emotional/conversational posture."""

    CONFUSED = "confused"
    EVASIVE = "evasive"
    PREJUDICED = "prejudiced"
    HOSTILE = "hostile"
    PLAYFUL = "playful"
    SINCERE = "sincere"
    VULNERABLE = "vulnerable"
    NEUTRAL = "neutral"


class ResponseShape(StrEnum):
    """Structural form of the response — length, rhythm, rhetorical arc."""

    ONE_HIT = "one_hit"
    SHORT_EXCHANGE = "short_exchange"
    LAYERED = "layered"
    PROBING = "probing"
    DENSE_CRITIQUE = "dense_critique"
    EXPRESSIVE_THINKING = "expressive_thinking"
    RAPID_FIRE = "rapid_fire"
    CONTRADICTION_CALLBACK = "contradiction_callback"


class StyleFlavor(StrEnum):
    """Tonal register of the response. Last two are Alvarado-inspired."""

    DRY = "dry"
    PHILOSOPHICAL = "philosophical"
    STREET = "street"
    CLINICAL = "clinical"
    IRONIC = "ironic"
    ECPHRASTIC = "ecphrastic"  # Alvarado: cultural description as lived experience
    REFLEXIVE = "reflexive"  # Alvarado: contemplative hypotaxis, self-qualifying prose
    METAPHORICAL = "metaphorical"


class ConversationPattern(StrEnum):
    """Meta-patterns detected across the recent turn history."""

    REPETITION_LOOP = "repetition_loop"
    PERFORMATIVE_ARGUING = "performative_arguing"
    DEFLECTION = "deflection"
    WINNING_VS_UNDERSTANDING = "winning_vs_understanding"
    NONE = "none"


# ═══════════════════════════════════════════════════════════════════════════
# Per-flow analysis results
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class EpistemicAnalysis:
    assertion_density: float
    hedging_score: float
    fluff_score: float
    contradiction_detected: bool
    vague_claim_count: int
    recommended_move: EpistemicMove
    move_reason: str


@dataclass
class PressureAnalysis:
    detected_state: UserState
    state_confidence: float
    pressure_level: int
    pressure_reason: str
    clamped_by_preset: bool


@dataclass
class ExpressionAnalysis:
    selected_shape: ResponseShape
    selected_flavor: StyleFlavor
    shape_reason: str
    flavor_reason: str
    repetition_avoided: list[str] = field(default_factory=list)


@dataclass
class AwarenessAnalysis:
    detected_pattern: ConversationPattern
    pattern_confidence: float
    meta_commentary: str | None
    delayed_question: str | None
    turns_in_pattern: int


# ═══════════════════════════════════════════════════════════════════════════
# Aggregated output of the whole pipeline
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class FlowAnalysis:
    """Full 4-flow analysis for a single turn.

    Produced by `FlowPipeline.run()`; consumed by `build_flow_prompt()` for
    injection into the system prompt, and by `validate_flow_adherence()`
    after generation to log violations."""

    epistemic: EpistemicAnalysis
    pressure: PressureAnalysis
    expression: ExpressionAnalysis
    awareness: AwarenessAnalysis
    agreement_streak: int = 0
    timestamp: float = field(default_factory=time.time)

    @property
    def any_active(self) -> bool:
        """True if any flow produced a non-default signal.

        Used by callers that only want to inject flow guidance when
        something interesting was detected (a default-abrasive, neutral-
        state, no-pattern turn adds no useful prompt overhead)."""
        return (
            self.epistemic.recommended_move != EpistemicMove.NONE
            or self.pressure.detected_state != UserState.NEUTRAL
            or self.awareness.detected_pattern != ConversationPattern.NONE
        )
