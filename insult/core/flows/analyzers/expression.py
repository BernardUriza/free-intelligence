"""Flow 3: Dynamic Expression — select response shape + style flavor.

Depends on prior analyzers' results (epistemic move, pressure level,
user state) and the expression history for anti-repetition. Because of
that coupling, ExpressionAnalyzer is the one that actively reads
`prior` in the Analyzer protocol.

Two sub-selections happen here:
- Shape: structural form (one-hit, probing, dense critique, ...)
- Flavor: tonal register (dry, ironic, street, ecphrastic, ...)

Both dodge the last 2-3 recent picks to keep the bot from sounding
stuck in a groove."""

from __future__ import annotations

import random
from typing import Any

import structlog

from insult.core.flows.analyzers.base import FlowContext
from insult.core.flows.patterns import (
    ECPHRASTIC_PATTERNS,
    REFLEXIVE_PATTERNS,
    count_hits,
)
from insult.core.flows.types import (
    EpistemicAnalysis,
    EpistemicMove,
    ExpressionAnalysis,
    PressureAnalysis,
    ResponseShape,
    StyleFlavor,
    UserState,
)
from insult.core.presets import PresetMode, PresetSelection

log = structlog.get_logger()


_SHAPE_ROTATION = [
    ResponseShape.SHORT_EXCHANGE,
    ResponseShape.ONE_HIT,
    ResponseShape.PROBING,
    ResponseShape.LAYERED,
    ResponseShape.DENSE_CRITIQUE,
    ResponseShape.EXPRESSIVE_THINKING,
    ResponseShape.RAPID_FIRE,
    ResponseShape.CONTRADICTION_CALLBACK,
]

_FLAVOR_ROTATION = [
    StyleFlavor.DRY,
    StyleFlavor.IRONIC,
    StyleFlavor.STREET,
    StyleFlavor.PHILOSOPHICAL,
    StyleFlavor.CLINICAL,
    StyleFlavor.ECPHRASTIC,
    StyleFlavor.REFLEXIVE,
    StyleFlavor.METAPHORICAL,
]


class ExpressionAnalyzer:
    name = "expression"

    def analyze(self, ctx: FlowContext, prior: dict[str, Any]) -> ExpressionAnalysis:
        epistemic: EpistemicAnalysis = prior["epistemic"]
        pressure: PressureAnalysis = prior["pressure"]

        if ctx.expression_history is not None and ctx.context_key is not None:
            recent_shapes = ctx.expression_history.recent_shapes(ctx.context_key)
            recent_flavors = ctx.expression_history.recent_flavors(ctx.context_key)
        else:
            recent_shapes = []
            recent_flavors = []

        shape, shape_reason, shape_avoided = self._select_shape(
            ctx.current_message, ctx.preset, pressure, epistemic, recent_shapes
        )
        flavor, flavor_reason, flavor_avoided = self._select_flavor(
            ctx.current_message, ctx.preset, pressure, recent_flavors
        )

        return ExpressionAnalysis(
            selected_shape=shape,
            selected_flavor=flavor,
            shape_reason=shape_reason,
            flavor_reason=flavor_reason,
            repetition_avoided=shape_avoided + flavor_avoided,
        )

    def log_event(self, result: ExpressionAnalysis) -> None:
        log.info(
            "flow_expression",
            shape=result.selected_shape.value,
            flavor=result.selected_flavor.value,
            shape_reason=result.shape_reason,
            flavor_reason=result.flavor_reason,
            avoided=result.repetition_avoided,
        )

    # -- Shape selection --

    @staticmethod
    def _select_shape(
        current_message: str,
        preset: PresetSelection,
        pressure: PressureAnalysis,
        epistemic: EpistemicAnalysis,
        recent_shapes: list[str],
    ) -> tuple[ResponseShape, str, list[str]]:
        word_count = len(current_message.split())
        avoided: list[str] = []

        # Priority cascade — first match wins. Order matters:
        #
        # 1. Safety carve-outs (pressure 5, vulnerable user) — these
        #    must override length reciprocity because the user's
        #    well-being trumps mirroring their text investment.
        # 2. Epistemic moves — semantic intent (compress / challenge)
        #    is meaningful regardless of input length.
        # 3. INTELLECTUAL_PRESSURE preset — explicitly dense by design.
        # 4. **Length reciprocity** — this branch was MISSING pre-PR2.5.
        #    Without it the PLAYFUL_ROAST / DEFAULT_ABRASIVE presets
        #    returned ONE_HIT to a 300-word user message, which Alex
        #    correctly described 2026-05-10 as feeling dismissive
        #    rather than sharp. The original Insult mirrored input
        #    length; the rewrite collapsed everything to ONE_HIT.
        # 5. Preset defaults (PLAYFUL_ROAST, ARC) — only reached for
        #    short inputs now, where ONE_HIT is genuinely warranted.
        # 6. Length heuristics for the residual neutral case.
        if pressure.pressure_level == 5:
            candidate = ResponseShape.ONE_HIT
            reason = "pressure_5_boundary"
        elif pressure.pressure_level == 1 and pressure.detected_state == UserState.VULNERABLE:
            candidate = ResponseShape.SHORT_EXCHANGE
            reason = "vulnerable_gentle"
        elif epistemic.recommended_move == EpistemicMove.COMPRESS:
            candidate = ResponseShape.ONE_HIT
            reason = "epistemic_compress"
        elif epistemic.recommended_move in (
            EpistemicMove.CHALLENGE_PREMISE,
            EpistemicMove.DEMAND_EVIDENCE,
        ):
            candidate = ResponseShape.PROBING
            reason = "epistemic_challenge"
        elif preset.mode == PresetMode.INTELLECTUAL_PRESSURE:
            candidate = ResponseShape.DENSE_CRITIQUE if word_count > 30 else ResponseShape.LAYERED
            reason = f"intellectual_wc={word_count}"

        # --- Length reciprocity (PR 2.5) ---
        # The original Insult responded "muchas cosas reales cortas
        # juntas que hacían un párrafo largo" — the LAYERED shape
        # captures exactly that texture. EXPRESSIVE_THINKING is a
        # close cousin used to add structural variety.
        elif word_count > 80:
            candidate = ResponseShape.LAYERED
            reason = f"reciprocity_long_wc={word_count}"
        elif word_count > 30:
            # 60/40 LAYERED vs EXPRESSIVE_THINKING. Both produce a
            # paragraph of stitched short fragments; the split breaks
            # structural monotony across consecutive medium-length turns.
            if random.random() < 0.60:
                candidate = ResponseShape.LAYERED
                reason = f"reciprocity_medium_wc={word_count}_layered"
            else:
                candidate = ResponseShape.EXPRESSIVE_THINKING
                reason = f"reciprocity_medium_wc={word_count}_expressive"

        elif preset.mode == PresetMode.PLAYFUL_ROAST:
            candidate = ResponseShape.ONE_HIT
            reason = "playful_preset"
        elif preset.mode == PresetMode.ARC:
            candidate = ResponseShape.LAYERED
            reason = "arc_preset"
        elif word_count < 8:
            candidate = ResponseShape.ONE_HIT
            reason = f"short_input_wc={word_count}"
        elif random.random() < 0.40:
            # 40% (up from 25% pre-PR2.5) chance of EXPRESSIVE_THINKING
            # on neutral/default messages — restores the fragmented-
            # paragraph texture Alex remembers from the original.
            candidate = ResponseShape.EXPRESSIVE_THINKING
            reason = "expressive_mode_random_activation"
        else:
            candidate = ResponseShape.SHORT_EXCHANGE
            reason = "default_short_exchange"

        # Anti-repetition: if the chosen shape matches either of the last
        # two, rotate to the first unused alternative in the rotation.
        if candidate.value in recent_shapes[-2:]:
            avoided.append(candidate.value)
            for alt in _SHAPE_ROTATION:
                if alt.value not in recent_shapes[-2:]:
                    candidate = alt
                    reason += f"_rotated_from_{avoided[0]}"
                    break

        return candidate, reason, avoided

    # -- Flavor selection --

    @staticmethod
    def _select_flavor(
        current_message: str,
        preset: PresetSelection,
        pressure: PressureAnalysis,
        recent_flavors: list[str],
    ) -> tuple[StyleFlavor, str, list[str]]:
        avoided: list[str] = []

        # Alvarado flavors fire when the content carries cultural/media
        # signals (ecphrastic) or existential questioning (reflexive).
        ecphrastic_hits = count_hits(current_message, ECPHRASTIC_PATTERNS)
        reflexive_hits = count_hits(current_message, REFLEXIVE_PATTERNS)

        if pressure.detected_state == UserState.PREJUDICED:
            candidate = StyleFlavor.CLINICAL
            reason = "prejudice_clinical"
        elif ecphrastic_hits >= 2:
            candidate = StyleFlavor.ECPHRASTIC
            reason = f"ecphrastic_signals={ecphrastic_hits}"
        elif reflexive_hits >= 2:
            candidate = StyleFlavor.REFLEXIVE
            reason = f"reflexive_signals={reflexive_hits}"
        elif pressure.detected_state == UserState.VULNERABLE and reflexive_hits >= 1:
            candidate = StyleFlavor.REFLEXIVE
            reason = "vulnerable_reflexive"
        elif preset.mode == PresetMode.ARC:
            candidate = StyleFlavor.PHILOSOPHICAL
            reason = "arc_philosophical"
        elif preset.mode == PresetMode.PLAYFUL_ROAST:
            candidate = StyleFlavor.IRONIC
            reason = "playful_ironic"
        elif preset.mode == PresetMode.INTELLECTUAL_PRESSURE:
            candidate = StyleFlavor.DRY
            reason = "intellectual_dry"
        elif pressure.detected_state == UserState.HOSTILE:
            candidate = StyleFlavor.STREET
            reason = "hostile_street"
        else:
            used_set = set(recent_flavors[-3:])
            candidate = next(
                (f for f in _FLAVOR_ROTATION if f.value not in used_set),
                StyleFlavor.DRY,
            )
            reason = "rotation_default"

        # Don't let the same flavor fire 3 turns in a row, even if the
        # rules above insist. Breaks dronemode for repeat triggers.
        if len(recent_flavors) >= 2 and all(f == candidate.value for f in recent_flavors[-2:]):
            avoided.append(candidate.value)
            for alt in _FLAVOR_ROTATION:
                if alt.value != candidate.value:
                    candidate = alt
                    reason += f"_rotated_from_{avoided[0]}"
                    break

        return candidate, reason, avoided
