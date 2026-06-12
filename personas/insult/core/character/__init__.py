"""Character package facade.

What used to be a 797-line `character.py` monolith is now a package with
focused submodules:

- ``detection``    — break/anti-pattern/clarification regexes + sanitize +
                     reinforcement constants (CHARACTER_REINFORCEMENT,
                     CONTEXT_REINFORCEMENT, IDENTITY_REINFORCEMENT_SUFFIX,
                     CACHE_BOUNDARY).
- ``formatting``   — post-generation mutators: normalize_formatting,
                     strip_echoed_quotes, strip_lists, enforce_length_variation,
                     deduplicate_opener, get_length_hint, strip_metadata.
- ``prompts``      — `build_adaptive_prompt`: layered system-prompt builder.

External callers keep importing names directly from
``insult.core.character`` — this facade re-exports the full public surface so
no callsite had to move when the split happened.
"""

from personas.insult.core.character.detection import (
    ANTI_PATTERN_CHECKS,
    CACHE_BOUNDARY,
    CHARACTER_BREAK_PATTERNS,
    CHARACTER_REINFORCEMENT,
    CLARIFICATION_DUMP_PATTERNS,
    CONTEXT_REINFORCEMENT,
    IDENTITY_REINFORCE_THRESHOLD,
    IDENTITY_REINFORCEMENT_SUFFIX,
    detect_anti_patterns,
    detect_break,
    detect_clarification_dump,
    sanitize,
)
from personas.insult.core.character.formatting import (
    deduplicate_opener,
    enforce_length_variation,
    get_length_hint,
    normalize_formatting,
    strip_echoed_quotes,
    strip_lists,
    strip_metadata,
)
from personas.insult.core.character.pipeline import (
    MutationStage,
    PipelineViolationError,
    preserve_min_length,
    preserve_question_marks,
    preserve_react_markers,
    run_pipeline,
)
from personas.insult.core.character.prompts import build_adaptive_prompt, compose_extra_layers

__all__ = [
    "ANTI_PATTERN_CHECKS",
    "CACHE_BOUNDARY",
    "CHARACTER_BREAK_PATTERNS",
    "CHARACTER_REINFORCEMENT",
    "CLARIFICATION_DUMP_PATTERNS",
    "CONTEXT_REINFORCEMENT",
    "IDENTITY_REINFORCEMENT_SUFFIX",
    "IDENTITY_REINFORCE_THRESHOLD",
    "MutationStage",
    "PipelineViolationError",
    "build_adaptive_prompt",
    "compose_extra_layers",
    "deduplicate_opener",
    "detect_anti_patterns",
    "detect_break",
    "detect_clarification_dump",
    "enforce_length_variation",
    "get_length_hint",
    "normalize_formatting",
    "preserve_min_length",
    "preserve_question_marks",
    "preserve_react_markers",
    "run_pipeline",
    "sanitize",
    "strip_echoed_quotes",
    "strip_lists",
    "strip_metadata",
]
