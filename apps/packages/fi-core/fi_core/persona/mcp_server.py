"""MCP server exposing fi_core.persona detectors as tools for AI agents.

Lets any MCP-compatible client (Claude Code, Cursor, Anthropic API with
MCP enabled, etc.) call into fi-core's character-integrity detection
WITHOUT depending on `fi-core` as a Python package in their own process.
The MCP transport handles cross-process invocation; the AI invokes the
tools as if they were native.

Install + register
------------------

::

    pip install 'fi-core[mcp]'
    claude mcp add fi-core-persona -- python -m fi_core.persona.mcp_server

Or run directly:

::

    python -m fi_core.persona.mcp_server  # stdio transport

Tools exposed
-------------

- ``check_drift(text, packs)`` — detect persona drift in a candidate
  LLM response. Returns matched patterns grouped by severity tier.
- ``list_packs()`` — discovery. Returns metadata for all built-in
  pattern packs (name, severity, language, pattern count).
- ``sanitize_response(text, packs)`` — last-resort cleanup. Removes
  sentences containing break-severity matches.
- ``get_reinforcement(pack_name)`` — return the reinforcement string
  that should be appended to the system prompt for retry. Auto-maps
  clarification-dump packs to CONTEXT_REINFORCEMENT, everything else
  to GENERIC_REINFORCEMENT.
- ``validate_and_retry_prompt(response, system_prompt, packs)`` —
  one-shot atomic loop: validates the response, decides per-severity
  whether retry is needed, returns the reinforced system prompt if
  so. Zero client-side orchestration.

Severity-tier decision rules (used by ``validate_and_retry_prompt``):

- Hard break match (identity leak)         -> retry with GENERIC_REINFORCEMENT
- Clarification-dump match (task-punting)  -> retry with CONTEXT_REINFORCEMENT
- Soft-drift match only (annoying tone)    -> NO retry, log + send anyway
- All clean                                -> NO retry, send response

The point of the atomic call: the AI does not need to interpret severity
itself, doesn't need to know which reinforcement applies to which
detection mode, doesn't need a state machine. One call, one decision.
"""

from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    raise ImportError(
        "fi_core.persona.mcp_server requires the MCP SDK. "
        "Install via: pip install 'fi-core[mcp]'"
    ) from e

from fi_core.persona import (
    AntiPatternMonitor,
    BreakDetector,
    ClarificationDumpDetector,
    sanitize as _sanitize,
)
from fi_core.persona import packs as _persona_packs

# ---------------------------------------------------------------------------
# Pack registry — single source of truth for the MCP-exposed packs.
#
# Maps pack name (the string clients pass over the wire) to a tuple of
# (compiled_patterns, severity_tier, language). Severity tier governs how
# matches are reported in check_drift output and which reinforcement is
# suggested for retry.
#
# Severity tiers:
#   - "break"               : hard identity leak. Retry-worthy.
#   - "soft_drift"          : assistant-tone / therapy-speak / etc. Log only.
#   - "clarification_dump"  : bot punting back to user. Retry with context.
# ---------------------------------------------------------------------------

# Atomic packs — each has a single, unambiguous severity tier.
_ATOMIC_PACKS: dict[str, tuple[list, str, str]] = {
    # Identity disclosure (break severity)
    "generic_ai_disclosure_en": (_persona_packs.GENERIC_AI_DISCLOSURE_EN, "break", "en"),
    "generic_ai_disclosure_es": (_persona_packs.GENERIC_AI_DISCLOSURE_ES, "break", "es"),
    # Assistant tone (soft drift)
    "assistant_tone_en": (_persona_packs.ASSISTANT_TONE_EN, "soft_drift", "en"),
    "assistant_tone_es": (_persona_packs.ASSISTANT_TONE_ES, "soft_drift", "es"),
    # Therapy speak / fake empathy (soft drift)
    "therapy_speak_en": (_persona_packs.THERAPY_SPEAK_EN, "soft_drift", "en"),
    "therapy_speak_es": (_persona_packs.THERAPY_SPEAK_ES, "soft_drift", "es"),
    # Summarizing / disclaiming (soft drift)
    "summarizing": (_persona_packs.SUMMARIZING, "soft_drift", "en+es"),
    # Roleplay stage directions like *sighs*, [pauses] (soft drift)
    "stage_directions": (_persona_packs.STAGE_DIRECTIONS, "soft_drift", "any"),
    # Markdown formatting drift (soft drift)
    "markdown_drift": (_persona_packs.MARKDOWN_DRIFT, "soft_drift", "any"),
    # Moralizing / preachy (soft drift)
    "moralizing_en": (_persona_packs.MORALIZING_EN, "soft_drift", "en"),
    "moralizing_es": (_persona_packs.MORALIZING_ES, "soft_drift", "es"),
    # Over-validation (soft drift)
    "over_validation_en": (_persona_packs.OVER_VALIDATION_EN, "soft_drift", "en"),
    "over_validation_es": (_persona_packs.OVER_VALIDATION_ES, "soft_drift", "es"),
    # Clarification dump — bot punting (its own tier)
    "clarification_dump_es": (_persona_packs.CLARIFICATION_DUMP_ES, "clarification_dump", "es"),
}

# Composite packs — convenience aliases that expand to a list of atomics.
# Composites preserve per-pattern severity by routing through their atomic
# components rather than flattening to a single tier.
_COMPOSITE_PACKS: dict[str, list[str]] = {
    "default_en": ["generic_ai_disclosure_en", "assistant_tone_en"],
    "default_es": ["generic_ai_disclosure_es", "assistant_tone_es"],
    "default_bilingual": [
        "generic_ai_disclosure_en",
        "generic_ai_disclosure_es",
        "assistant_tone_en",
        "assistant_tone_es",
    ],
    "all_ai_disclosure": ["generic_ai_disclosure_en", "generic_ai_disclosure_es"],
    "all_assistant_tone": ["assistant_tone_en", "assistant_tone_es"],
    "all_therapy_speak": ["therapy_speak_en", "therapy_speak_es"],
    "all_moralizing": ["moralizing_en", "moralizing_es"],
    "all_over_validation": ["over_validation_en", "over_validation_es"],
}

# Default packs used when the caller does not specify any.
_DEFAULT_PACK_NAMES = ["default_bilingual"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_packs(
    names: list[str] | None,
) -> tuple[list[tuple[str, list, str]], list[str]]:
    """Resolve pack names to (name, patterns, severity) tuples.

    Composites are expanded to their atomic components so per-pattern
    severity is preserved end-to-end (a hard break inside ``default_bilingual``
    is still routed through the break-tier detector, not the soft-drift one).

    Unknown names are collected in a separate ``unknown`` list rather
    than raising — clients can request experimental pack names without
    breaking the call.

    Returns:
        (resolved, unknown) where:
          resolved = [(atomic_name, patterns, severity), ...]
          unknown  = [name, ...]  # names the server does not recognize
    """
    names = names or _DEFAULT_PACK_NAMES
    resolved: list[tuple[str, list, str]] = []
    unknown: list[str] = []
    seen_atomics: set[str] = set()

    for name in names:
        if name in _COMPOSITE_PACKS:
            # Expand composite to atomics.
            for atomic_name in _COMPOSITE_PACKS[name]:
                if atomic_name in seen_atomics:
                    continue
                patterns, severity, _lang = _ATOMIC_PACKS[atomic_name]
                resolved.append((atomic_name, patterns, severity))
                seen_atomics.add(atomic_name)
        elif name in _ATOMIC_PACKS:
            if name in seen_atomics:
                continue
            patterns, severity, _lang = _ATOMIC_PACKS[name]
            resolved.append((name, patterns, severity))
            seen_atomics.add(name)
        else:
            unknown.append(name)

    return resolved, unknown


def _reinforcement_for(pack_name: str | None) -> str:
    """Auto-derive the reinforcement string for a pack.

    Convention: pack names containing 'clarification_dump' map to
    CONTEXT_REINFORCEMENT; all other packs (including custom packs
    the server does not know about) default to GENERIC_REINFORCEMENT.

    The atomic ``validate_and_retry_prompt`` tool uses this mapping
    so the AI does not need to know about reinforcement variants.
    """
    if pack_name and "clarification_dump" in pack_name.lower():
        return _persona_packs.CONTEXT_REINFORCEMENT
    return _persona_packs.GENERIC_REINFORCEMENT


# ---------------------------------------------------------------------------
# MCP server + tools
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "fi-core-persona",
    instructions=(
        "Character-integrity / anti-drift detection for LLM outputs. "
        "Use this server to validate your own responses before sending them "
        "to the user. The primary entry point is `validate_and_retry_prompt` "
        "— it returns whether retry is needed and the reinforced system "
        "prompt in a single call. Use `check_drift` for granular inspection. "
        "Use `list_packs` to discover available pattern packs."
    ),
)


@mcp.tool()
async def list_packs() -> dict:
    """List all built-in pattern packs available on this server.

    Returns a dictionary with one entry per pack: its severity tier
    (``break``, ``soft_drift``, ``clarification_dump``, or ``mixed`` for
    composites), language code (``en``, ``es``, ``en+es``, ``any``), and
    pattern count.

    Use the names returned here as ``packs`` arguments to ``check_drift``,
    ``sanitize_response``, and ``validate_and_retry_prompt``.

    Returned shape::

        {
          "atomic_packs": [
            {"name", "severity", "language", "pattern_count"},
            ...
          ],
          "composite_packs": [
            {"name", "expands_to": [atomic_name, ...]},
            ...
          ],
          "default": [pack_name, ...],
        }
    """
    return {
        "atomic_packs": [
            {
                "name": name,
                "severity": severity,
                "language": language,
                "pattern_count": len(patterns),
            }
            for name, (patterns, severity, language) in _ATOMIC_PACKS.items()
        ],
        "composite_packs": [
            {"name": name, "expands_to": expansion}
            for name, expansion in _COMPOSITE_PACKS.items()
        ],
        "default": _DEFAULT_PACK_NAMES,
    }


@mcp.tool()
async def check_drift(
    text: str,
    packs: list[str] | None = None,
) -> dict:
    """Detect persona drift in ``text`` using the listed packs.

    Matches are grouped by severity tier so the caller knows which
    require a retry vs which are log-only soft drift.

    Args:
        text: The candidate LLM response to validate.
        packs: List of pack names to apply. If None or empty, uses
            ``default_bilingual`` (covers EN + ES AI disclosure + tone).
            Use ``list_packs()`` to discover available names.

    Returns:
        ``{
            "clean": bool,                       # True iff no matches
            "matched_break": [pattern, ...],     # hard breaks
            "matched_soft_drift": [pattern, ...],# soft drift
            "matched_clarification_dump": [pattern, ...],
            "packs_applied": [name, ...],        # echoed for traceability
            "packs_unknown": [name, ...],        # caller-supplied names not in registry
        }``
    """
    resolved, unknown = _resolve_packs(packs)
    applied_names = [name for name, _, _ in resolved]

    matched_break: list[str] = []
    matched_soft: list[str] = []
    matched_clarif: list[str] = []

    for _name, patterns, severity in resolved:
        if severity == "break":
            detector = BreakDetector(patterns=patterns)
            matched_break.extend(detector.detect(text))
        elif severity == "clarification_dump":
            detector = ClarificationDumpDetector(patterns=patterns)
            matched_clarif.extend(detector.detect(text))
        elif severity == "soft_drift":
            monitor = AntiPatternMonitor(patterns=patterns)
            matched_soft.extend(monitor.detect(text))

    # Deduplicate while preserving order.
    def _uniq(seq: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    matched_break = _uniq(matched_break)
    matched_soft = _uniq(matched_soft)
    matched_clarif = _uniq(matched_clarif)

    return {
        "clean": not (matched_break or matched_soft or matched_clarif),
        "matched_break": matched_break,
        "matched_soft_drift": matched_soft,
        "matched_clarification_dump": matched_clarif,
        "packs_applied": applied_names,
        "packs_unknown": unknown,
    }


@mcp.tool()
async def sanitize_response(
    text: str,
    packs: list[str] | None = None,
) -> dict:
    """Last-resort: remove sentences containing break-severity matches.

    Use only when retry-with-reinforcement has already failed. Splits
    ``text`` on sentence-ending punctuation, drops sentences with any
    match against the union of pack patterns, joins what remains.

    If sanitization would remove every sentence, returns ``text``
    unchanged (the caller decides whether to drop or send-anyway —
    this tool does not silently destroy data).

    Args:
        text: Original response.
        packs: Pack names to use for the sentence filter. If None,
            uses ``default_bilingual``.

    Returns:
        ``{"sanitized": str, "would_remove_all": bool}``
    """
    resolved, _unknown = _resolve_packs(packs)
    all_patterns: list = []
    for _name, patterns, _sev in resolved:
        all_patterns.extend(patterns)

    cleaned = _sanitize(text, patterns=all_patterns)
    return {
        "sanitized": cleaned,
        "would_remove_all": cleaned == text
        and bool(all_patterns)
        and any(p.search(text) for p in all_patterns),
    }


@mcp.tool()
async def get_reinforcement(pack_name: str | None = None) -> dict:
    """Return the reinforcement string suitable for a specific pack.

    The reinforcement is appended to the system prompt before retrying
    the LLM call. Convention:

    - Pack names containing ``clarification_dump`` -> ``CONTEXT_REINFORCEMENT``
    - All other packs (incl. unknown / custom) -> ``GENERIC_REINFORCEMENT``

    For long-conversation identity-reinforcement (a suffix, not a
    standalone reinforcement), use ``IDENTITY_REINFORCEMENT_SUFFIX``
    from the Python package directly — it is not exposed here because
    it composes with the existing system prompt rather than replacing
    a retry path.

    Args:
        pack_name: Name of the pack that produced the drift, or None
            for the default GENERIC_REINFORCEMENT.

    Returns:
        ``{"reinforcement": str, "applies_to": str}``
    """
    reinforcement = _reinforcement_for(pack_name)
    return {
        "reinforcement": reinforcement,
        "applies_to": pack_name or "default",
    }


@mcp.tool()
async def validate_and_retry_prompt(
    response: str,
    system_prompt: str,
    packs: list[str] | None = None,
) -> dict:
    """Atomic loop: validate ``response``, decide retry, return new prompt.

    This is the killer-loop tool. It collapses ``check_drift`` +
    ``get_reinforcement`` + the retry-decision logic into a single
    call so the consuming AI does not orchestrate state.

    Decision rules:

    - **Hard break match** (identity leak):
      ``retry_needed=True``, ``reinforced_system_prompt = system_prompt + GENERIC_REINFORCEMENT``.
    - **Clarification-dump match** (bot punting back at user):
      ``retry_needed=True``, ``reinforced_system_prompt = system_prompt + CONTEXT_REINFORCEMENT``.
    - **Soft-drift match only** (annoying-tone tier):
      ``retry_needed=False``. Log the matches; send the response.
    - **All clean**:
      ``retry_needed=False``. ``reinforced_system_prompt`` is None.

    Both break and clarification-dump matches can fire in the same
    response. When both are present, break takes precedence in the
    returned reinforcement (since identity is the more severe failure).

    Args:
        response: LLM response to validate.
        system_prompt: The system prompt that was used to generate the
            response. The reinforced prompt is built by appending to
            this string.
        packs: Pack names to apply. If None, ``default_bilingual``.

    Returns:
        ``{
            "clean": bool,
            "retry_needed": bool,
            "reinforced_system_prompt": str | None,
            "matched": {
                "break": [pattern, ...],
                "soft_drift": [pattern, ...],
                "clarification_dump": [pattern, ...],
            },
        }``
    """
    detection = await check_drift(text=response, packs=packs)

    has_break = bool(detection["matched_break"])
    has_clarif = bool(detection["matched_clarification_dump"])
    retry_needed = has_break or has_clarif

    reinforced_prompt: str | None = None
    if retry_needed:
        # Break takes precedence over clarification dump.
        reinforcement = (
            _persona_packs.GENERIC_REINFORCEMENT
            if has_break
            else _persona_packs.CONTEXT_REINFORCEMENT
        )
        reinforced_prompt = system_prompt + reinforcement

    return {
        "clean": detection["clean"],
        "retry_needed": retry_needed,
        "reinforced_system_prompt": reinforced_prompt,
        "matched": {
            "break": detection["matched_break"],
            "soft_drift": detection["matched_soft_drift"],
            "clarification_dump": detection["matched_clarification_dump"],
        },
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
