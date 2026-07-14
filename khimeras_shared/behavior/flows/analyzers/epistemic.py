"""Flow 1: Epistemic Control — truthfulness, precision, argumentative quality.

Scores the current message on four axes (assertion density, hedging,
fluff, vague claims) plus contradiction detection against prior user
turns, and recommends one of the `EpistemicMove` enum values. Pure
regex — no LLM calls."""

from __future__ import annotations

import re
from typing import Any

import structlog

from khimeras_shared.behavior.flows.analyzers.base import FlowContext
from khimeras_shared.behavior.flows.model.patterns import (
    ASSERTION_PATTERNS,
    FLUFF_PATTERNS,
    HEDGING_PATTERNS,
    NEGATION_PAIRS,
    STOPWORDS,
    VAGUE_CLAIM_PATTERNS,
    count_hits,
)
from khimeras_shared.behavior.flows.model.types import EpistemicAnalysis, EpistemicMove

log = structlog.get_logger()


class EpistemicAnalyzer:
    name = "epistemic"

    def analyze(self, ctx: FlowContext, prior: dict[str, Any]) -> EpistemicAnalysis:
        return self._score(ctx.current_message, ctx.user_messages)

    def log_event(self, result: EpistemicAnalysis) -> None:
        log.info(
            "flow_epistemic",
            assertion_density=result.assertion_density,
            hedging_score=result.hedging_score,
            fluff_score=result.fluff_score,
            contradiction=result.contradiction_detected,
            vague_claims=result.vague_claim_count,
            move=result.recommended_move.value,
            reason=result.move_reason,
        )

    # -- Internals --

    @staticmethod
    def _detect_contradiction(current: str, prior_messages: list[str]) -> bool:
        """True if current message negates a claim from a prior message with
        2+ shared content words. Cheap heuristic, not semantic — we'd rather
        miss a subtle one than cry contradiction on unrelated topics."""
        current_words = {w.lower() for w in current.split() if len(w) > 3 and w.lower() not in STOPWORDS}

        for neg_pat, aff_pat in NEGATION_PAIRS:
            if neg_pat.search(current):
                for prior in prior_messages:
                    if aff_pat.search(prior) and not neg_pat.search(prior):
                        prior_words = {w.lower() for w in prior.split() if len(w) > 3 and w.lower() not in STOPWORDS}
                        if len(current_words & prior_words) >= 2:
                            return True
        return False

    def _score(self, current_message: str, user_messages: list[str]) -> EpistemicAnalysis:
        words = current_message.split()
        word_count = max(len(words), 1)
        sentences = [s for s in re.split(r"[.!?]+", current_message) if s.strip()]
        sentence_count = max(len(sentences), 1)

        assertion_hits = sum(1 for p in ASSERTION_PATTERNS for s in sentences if p.search(s))
        assertion_density = min(assertion_hits / sentence_count, 1.0)

        hedging_hits = count_hits(current_message, HEDGING_PATTERNS)
        hedging_score = min(hedging_hits / word_count * 5, 1.0)

        fluff_hits = count_hits(current_message, FLUFF_PATTERNS)
        fluff_score = min(fluff_hits / word_count * 5, 1.0)

        vague_claim_count = count_hits(current_message, VAGUE_CLAIM_PATTERNS)
        contradiction_detected = self._detect_contradiction(current_message, user_messages)

        # Decision priority (first match wins): contradiction > fluff > vague >
        # strong unhedged assertion > mixed hedge+assert > nothing.
        if contradiction_detected:
            move = EpistemicMove.CALL_CONTRADICTION
            reason = "user_contradicts_prior_statement"
        elif fluff_score >= 0.3 and word_count > 15:
            move = EpistemicMove.COMPRESS
            reason = f"fluff={fluff_score:.2f}_words={word_count}"
        elif vague_claim_count >= 2:
            move = EpistemicMove.DEMAND_EVIDENCE
            reason = f"vague_claims={vague_claim_count}"
        elif assertion_density >= 0.6 and hedging_score < 0.1:
            move = EpistemicMove.CHALLENGE_PREMISE
            reason = f"assertion={assertion_density:.2f}_hedging={hedging_score:.2f}"
        elif hedging_score >= 0.3 and assertion_density >= 0.3:
            move = EpistemicMove.CONCEDE_PARTIAL
            reason = f"mixed_hedging={hedging_score:.2f}_assertion={assertion_density:.2f}"
        else:
            move = EpistemicMove.NONE
            reason = "no_epistemic_signal"

        return EpistemicAnalysis(
            assertion_density=round(assertion_density, 2),
            hedging_score=round(hedging_score, 2),
            fluff_score=round(fluff_score, 2),
            contradiction_detected=contradiction_detected,
            vague_claim_count=vague_claim_count,
            recommended_move=move,
            move_reason=reason,
        )
