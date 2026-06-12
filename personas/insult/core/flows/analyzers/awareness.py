"""Flow 4: Conversational Awareness — meta-pattern detection.

Detects patterns that span multiple turns: repetition loops,
performative arguing, deflection, winning-vs-understanding. These are
the things that need NAMING out loud, not arguing with — the bot's
response should typically break the pattern rather than feed it."""

from __future__ import annotations

from typing import Any

import structlog

from personas.insult.core.flows.analyzers.base import FlowContext
from personas.insult.core.flows.patterns import (
    DEFLECTION_PATTERNS,
    JACCARD_THRESHOLD,
    MIN_LOOP_CONSECUTIVE,
    PERFORMATIVE_PATTERNS,
    STOPWORDS,
    WINNING_PATTERNS,
    count_hits,
)
from personas.insult.core.flows.types import AwarenessAnalysis, ConversationPattern

log = structlog.get_logger()


class AwarenessAnalyzer:
    name = "awareness"

    def analyze(self, ctx: FlowContext, prior: dict[str, Any]) -> AwarenessAnalysis:
        return self._score(ctx.current_message, ctx.recent_messages)

    def log_event(self, result: AwarenessAnalysis) -> None:
        log.info(
            "flow_awareness",
            pattern=result.detected_pattern.value,
            confidence=result.pattern_confidence,
            turns_in_pattern=result.turns_in_pattern,
            has_meta=result.meta_commentary is not None,
            has_delayed_question=result.delayed_question is not None,
        )

    # -- Internals --

    @staticmethod
    def _detect_repetition_loop(user_messages: list[str]) -> tuple[bool, int]:
        """Count consecutive pairs of user messages whose content words
        overlap above JACCARD_THRESHOLD. Returns (is_loop, consecutive_count).

        The Jaccard metric is symmetric and scale-invariant — 40% overlap
        between "tengo miedo del futuro" and "me preocupa el futuro"
        counts as similar even though they share no exact n-gram."""
        if len(user_messages) < 3:
            return False, 0

        def content_words(text: str) -> set[str]:
            return {w.lower() for w in text.split() if len(w) > 2 and w.lower() not in STOPWORDS}

        consecutive_similar = 0
        for i in range(len(user_messages) - 1):
            w1 = content_words(user_messages[i])
            w2 = content_words(user_messages[i + 1])
            union = w1 | w2
            if union:
                jaccard = len(w1 & w2) / len(union)
                if jaccard > JACCARD_THRESHOLD:
                    consecutive_similar += 1
                else:
                    consecutive_similar = 0

        return consecutive_similar >= MIN_LOOP_CONSECUTIVE, consecutive_similar

    def _score(
        self,
        current_message: str,
        recent_messages: list[dict],
    ) -> AwarenessAnalysis:
        user_messages = [m["content"] for m in recent_messages if m.get("role") == "user"][-8:]

        repetition, rep_turns = self._detect_repetition_loop(user_messages)

        performative_score = float(count_hits(current_message, PERFORMATIVE_PATTERNS))
        deflection_score = float(count_hits(current_message, DEFLECTION_PATTERNS))
        winning_score = float(count_hits(current_message, WINNING_PATTERNS))

        # Window bonus for sticky patterns (performative + winning). A
        # single mention is weak signal; recurrence across the window is
        # stronger even if the current message is mild.
        for msg in user_messages[-4:-1] if len(user_messages) >= 2 else []:
            performative_score += count_hits(msg, PERFORMATIVE_PATTERNS) * 0.5
            winning_score += count_hits(msg, WINNING_PATTERNS) * 0.5

        # Priority: repetition > winning > performative > deflection.
        # Repetition takes top because it encompasses all the others —
        # a looping user IS arguing performatively, but calling the loop
        # is the productive move.
        if repetition and rep_turns >= MIN_LOOP_CONSECUTIVE:
            pattern = ConversationPattern.REPETITION_LOOP
            confidence = min(rep_turns / 4.0, 1.0)
            turns = rep_turns
            meta = "You keep circling the same point. Either say something new or sit with why you're stuck."
            question = None
        elif winning_score >= 2:
            pattern = ConversationPattern.WINNING_VS_UNDERSTANDING
            confidence = min(winning_score / 3.0, 1.0)
            turns = int(winning_score)
            meta = "You're trying to win this, not understand it. Different game."
            question = "What would change your mind? If nothing — why are we even talking?"
        elif performative_score >= 2:
            pattern = ConversationPattern.PERFORMATIVE_ARGUING
            confidence = min(performative_score / 3.0, 1.0)
            turns = int(performative_score)
            meta = None
            question = "Forget what you've been saying. What do you actually believe?"
        elif deflection_score >= 1:
            pattern = ConversationPattern.DEFLECTION
            confidence = min(deflection_score / 2.0, 1.0)
            turns = int(deflection_score)
            meta = "Nice redirect. Now answer the actual question."
            question = None
        else:
            pattern = ConversationPattern.NONE
            confidence = 0.0
            turns = 0
            meta = None
            question = None

        return AwarenessAnalysis(
            detected_pattern=pattern,
            pattern_confidence=round(confidence, 2),
            meta_commentary=meta,
            delayed_question=question,
            turns_in_pattern=turns,
        )
