"""FlowPipeline — runs the analyzers in order and applies cross-flow rules.

Design notes:

The pipeline owns THREE responsibilities beyond just calling analyzers:

1. **Context hydration**: builds `FlowContext` once (including the last
   N user messages extraction) so each analyzer receives pre-derived
   fields rather than re-deriving them.

2. **Cross-flow overrides**: awareness results can mutate the expression
   plan (repetition → ONE_HIT, deflection → PROBING), and a vulnerable
   user state suppresses aggressive epistemic moves. These rules live
   here, not inside individual analyzers, because they require knowing
   multiple analyzer outputs together.

3. **Telemetry emission**: each analyzer emits its own structured event;
   the pipeline only coordinates ordering so events ship in a stable
   sequence that makes log parsing predictable.

Why Pipeline + Protocol instead of a giant `analyze_flows` function:

- Adding a 5th flow = create a new Analyzer class + append to list.
- Mocking a specific analyzer in tests = replace one entry in the list.
- Running a subset (e.g. only epistemic for a lightweight path) = pass
  a filtered list to the pipeline constructor.
- Each flow can evolve its internals without touching orchestration.
"""

from __future__ import annotations

from personas.insult.core.flows.analyzers import (
    Analyzer,
    AwarenessAnalyzer,
    EpistemicAnalyzer,
    ExpressionAnalyzer,
    FlowContext,
    PressureAnalyzer,
)
from personas.insult.core.flows.history import ExpressionHistory
from personas.insult.core.flows.patterns import AGREEMENT_RE
from personas.insult.core.flows.types import (
    ConversationPattern,
    EpistemicAnalysis,
    EpistemicMove,
    FlowAnalysis,
    ResponseShape,
    UserState,
)
from personas.insult.core.presets import PresetSelection

# Default analyzer ordering. Order matters because ExpressionAnalyzer
# reads the prior results of epistemic + pressure, and cross-flow
# overrides downstream assume all 4 have already run.
DEFAULT_ANALYZERS: list[type[Analyzer]] = [
    EpistemicAnalyzer,
    PressureAnalyzer,
    ExpressionAnalyzer,
    AwarenessAnalyzer,
]


class FlowPipeline:
    """Coordinator that runs a list of Analyzers and applies cross-flow rules.

    Instances are cheap to create — analyzers hold no per-turn state
    (they receive the FlowContext freshly each call). The ExpressionHistory
    is per-pipeline-caller because it's bound to a channel+user, not to
    the analyzer itself."""

    def __init__(self, analyzers: list[Analyzer] | None = None):
        if analyzers is None:
            analyzers = [cls() for cls in DEFAULT_ANALYZERS]
        self._analyzers = analyzers

    def run(
        self,
        current_message: str,
        recent_messages: list[dict],
        preset: PresetSelection,
        expression_history: ExpressionHistory,
        context_key: str,
    ) -> FlowAnalysis:
        """Execute the full pipeline and return the aggregated FlowAnalysis."""
        user_messages = [m["content"] for m in recent_messages if m.get("role") == "user"][-10:]

        ctx = FlowContext(
            current_message=current_message,
            recent_messages=recent_messages,
            preset=preset,
            user_messages=user_messages,
            expression_history=expression_history,
            context_key=context_key,
        )

        results: dict[str, object] = {}
        for analyzer in self._analyzers:
            results[analyzer.name] = analyzer.analyze(ctx, results)

        # Strong-typed unpacking (the protocol returns Any). If the
        # default analyzer list changed under us, bail loudly rather
        # than produce a malformed FlowAnalysis.
        epistemic = results["epistemic"]
        pressure = results["pressure"]
        expression = results["expression"]
        awareness = results["awareness"]

        # Cross-flow override #1: awareness patterns reshape expression.
        # A repetition loop should land as a ONE_HIT call-out; a detected
        # deflection should be answered with a PROBING question.
        if awareness.detected_pattern == ConversationPattern.REPETITION_LOOP:  # type: ignore[attr-defined]
            expression.selected_shape = ResponseShape.ONE_HIT  # type: ignore[attr-defined]
            expression.shape_reason += "_override_repetition_loop"  # type: ignore[attr-defined]
        elif awareness.detected_pattern == ConversationPattern.DEFLECTION:  # type: ignore[attr-defined]
            expression.selected_shape = ResponseShape.PROBING  # type: ignore[attr-defined]
            expression.shape_reason += "_override_deflection"  # type: ignore[attr-defined]

        # Cross-flow override #2: aggressive epistemic moves are
        # suppressed when the pressure flow says the user is vulnerable.
        # Challenging premises or demanding evidence from someone sharing
        # a wound is a misread — the epistemic signal still gets
        # observed (for telemetry) but the move is nulled.
        if (
            pressure.detected_state == UserState.VULNERABLE  # type: ignore[attr-defined]
            and epistemic.recommended_move  # type: ignore[attr-defined]
            in (
                EpistemicMove.CHALLENGE_PREMISE,
                EpistemicMove.DEMAND_EVIDENCE,
                EpistemicMove.COMPRESS,
            )
        ):
            epistemic = EpistemicAnalysis(  # type: ignore[misc]
                assertion_density=epistemic.assertion_density,  # type: ignore[attr-defined]
                hedging_score=epistemic.hedging_score,  # type: ignore[attr-defined]
                fluff_score=epistemic.fluff_score,  # type: ignore[attr-defined]
                contradiction_detected=epistemic.contradiction_detected,  # type: ignore[attr-defined]
                vague_claim_count=epistemic.vague_claim_count,  # type: ignore[attr-defined]
                recommended_move=EpistemicMove.NONE,
                move_reason=epistemic.move_reason + "_suppressed_vulnerable",  # type: ignore[attr-defined]
            )

        # Persist the selected shape+flavor AFTER overrides so future
        # turns see the effective choice, not the pre-override one.
        expression_history.record(
            context_key,
            expression.selected_shape,  # type: ignore[attr-defined]
            expression.selected_flavor,  # type: ignore[attr-defined]
        )

        # Agreement streak: how many consecutive recent assistant
        # messages started with "exacto/tienes razón/etc" — used by the
        # anti-sycophancy monitoring downstream. Up to 5 recent.
        assistant_msgs = [m for m in (recent_messages or []) if m.get("role") == "assistant"][-5:]
        streak = 0
        for m in reversed(assistant_msgs):
            if AGREEMENT_RE.search(m.get("content", "")):
                streak += 1
            else:
                break

        analysis = FlowAnalysis(
            epistemic=epistemic,  # type: ignore[arg-type]
            pressure=pressure,  # type: ignore[arg-type]
            expression=expression,  # type: ignore[arg-type]
            awareness=awareness,  # type: ignore[arg-type]
            agreement_streak=streak,
        )

        # Emit telemetry last so downstream parsers always see the
        # post-override state (matches what the prompt will contain).
        for analyzer in self._analyzers:
            analyzer.log_event(results[analyzer.name] if analyzer.name != "epistemic" else epistemic)

        return analysis


# Singleton convenience: most callers want the default pipeline.
# Build once at import time so every call doesn't re-instantiate the
# four analyzer objects.
_DEFAULT_PIPELINE = FlowPipeline()


def analyze_flows(
    current_message: str,
    recent_messages: list[dict],
    preset: PresetSelection,
    expression_history: ExpressionHistory,
    context_key: str,
) -> FlowAnalysis:
    """Legacy façade — runs the default pipeline.

    Preserves the pre-refactor function signature so existing callers
    (chat cog, character guard tests) don't need to know about the
    FlowPipeline class."""
    return _DEFAULT_PIPELINE.run(
        current_message,
        recent_messages,
        preset,
        expression_history,
        context_key,
    )
