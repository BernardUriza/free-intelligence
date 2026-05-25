"""fi_runner.packs — persona drift/reinforcement packs, re-exported from fi-core.

A thin consumer of fi-runner (a runner in another repo) only knows fi-runner —
it must NOT import fi-core directly (fi-runner is the single boundary over
fi-core). But to build a guard like ``antidrift_guard(break_patterns=[...])`` it
needs fi-core's pattern packs. fi-runner DOES depend on fi-core, so it re-exports
them here: the consumer does ``from fi_runner import packs`` (or
``from fi_runner.packs import ALL_AI_DISCLOSURE``), never ``import fi_core``.

Each symbol is the SAME object as in :mod:`fi_core.persona.packs` (a re-export,
not a copy). Kept explicit (no ``import *``) so the surface is auditable; the
test suite asserts no public pack is missing.
"""

from __future__ import annotations

from fi_core.persona.packs import (
    ALL_AI_DISCLOSURE,
    ALL_ASSISTANT_TONE,
    ALL_MORALIZING,
    ALL_OVER_VALIDATION,
    ALL_THERAPY_SPEAK,
    ASSISTANT_TONE_EN,
    ASSISTANT_TONE_ES,
    CLARIFICATION_DUMP_ES,
    CONTEXT_REINFORCEMENT,
    DEFAULT_BILINGUAL,
    DEFAULT_EN,
    DEFAULT_ES,
    GENERIC_AI_DISCLOSURE_EN,
    GENERIC_AI_DISCLOSURE_ES,
    GENERIC_REINFORCEMENT,
    IDENTITY_REINFORCEMENT_SUFFIX,
    MARKDOWN_DRIFT,
    MORALIZING_EN,
    MORALIZING_ES,
    OVER_VALIDATION_EN,
    OVER_VALIDATION_ES,
    STAGE_DIRECTIONS,
    SUMMARIZING,
    THERAPY_SPEAK_EN,
    THERAPY_SPEAK_ES,
)

__all__ = [
    "ALL_AI_DISCLOSURE",
    "ALL_ASSISTANT_TONE",
    "ALL_MORALIZING",
    "ALL_OVER_VALIDATION",
    "ALL_THERAPY_SPEAK",
    "ASSISTANT_TONE_EN",
    "ASSISTANT_TONE_ES",
    "CLARIFICATION_DUMP_ES",
    "CONTEXT_REINFORCEMENT",
    "DEFAULT_BILINGUAL",
    "DEFAULT_EN",
    "DEFAULT_ES",
    "GENERIC_AI_DISCLOSURE_EN",
    "GENERIC_AI_DISCLOSURE_ES",
    "GENERIC_REINFORCEMENT",
    "IDENTITY_REINFORCEMENT_SUFFIX",
    "MARKDOWN_DRIFT",
    "MORALIZING_EN",
    "MORALIZING_ES",
    "OVER_VALIDATION_EN",
    "OVER_VALIDATION_ES",
    "STAGE_DIRECTIONS",
    "SUMMARIZING",
    "THERAPY_SPEAK_EN",
    "THERAPY_SPEAK_ES",
]
