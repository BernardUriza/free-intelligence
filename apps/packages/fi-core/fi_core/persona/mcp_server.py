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
# Consolidation tools (v0.5.1) — Shape B per [[mcp-shape-b-canonical]]
# ---------------------------------------------------------------------------
# fi-core does NOT execute the LLM. These tools BUILD the judge prompt and
# PARSE the raw response. The consumer (insult-runner, AURITY, fi-monitor)
# holds the LLM credentials and orchestrates the call.

_CONSOLIDATION_JUDGE_SYSTEM_PROMPT = """\
You are a memory curator for a long-term assistant. You will be given the COMPLETE current set of stored facts about a single user. Some are duplicates, some are stale, some contradict newer entries. Your job is to produce a curation plan as JSON.

Each input fact has an integer "id" you must reference verbatim in your output.

For each fact, decide ONE of:
- "NOOP"   — keep as-is, no overlap with others
- "DELETE" — remove (duplicate of a kept fact, contradicted by newer fact, or no longer accurate)
- "UPDATE" — supersede this fact with merged or corrected text. Use when two or more facts cover the same topic and you want to fold them into one cleaner sentence.

Hard rules:
- Treat the LATEST `updated_at` as authoritative when two facts conflict. The newer one wins; the older one is DELETEd.
- Never DELETE a fact unless another fact in the input set covers the same ground OR the fact is plainly contradicted. If a fact stands alone, NOOP it.
- An UPDATE consumes one or more original ids and produces ONE new merged fact text. List the consumed ids in "merge_ids".
- Preserve language: if the original facts are in Spanish, the merged text must be in Spanish. Same for English.
- Preserve concrete detail. Dates, place names, numbers, names of people must survive. Don't generalize "el 20 abril 2026 lo catearon en aduana" into "tuvo un problema en la frontera".
- Keep merged facts under 25 words.

Return ONLY a JSON array. Each element is an operation object:

  {"op": "NOOP",   "id": 12, "reason": "standalone fact"}
  {"op": "DELETE", "id": 17, "reason": "duplicate of id=12"}
  {"op": "UPDATE", "merge_ids": [3, 8], "new_fact": "...", "category": "...", "reason": "..."}

Every input fact id MUST appear in exactly one operation (as `id` for NOOP/DELETE or inside `merge_ids` for UPDATE). Do not invent new facts that aren't a merge of existing ones.

Return the JSON array and nothing else.
"""


def _render_facts_as_user_prompt(facts: list[dict]) -> str:
    """Render the user's fact set as a JSON array string for the judge.

    Each fact must have `id`, `fact`, optional `category`, and
    `updated_at` (unix seconds). The render formats `updated_at` as an
    ISO date for the model so age comparisons are intuitive.
    """
    import json as _json
    import time as _time

    lines = []
    for f in facts:
        ts = f.get("updated_at") or 0
        when = _time.strftime("%Y-%m-%d", _time.gmtime(ts)) if ts else "unknown"
        lines.append(
            f'{{"id": {f["id"]}, "fact": {_json.dumps(f["fact"], ensure_ascii=False)}, '
            f'"category": "{f.get("category", "general")}", "updated_at": "{when}"}}'
        )
    return "Current facts:\n[\n  " + ",\n  ".join(lines) + "\n]"


@mcp.tool()
async def build_consolidation_prompt(
    facts: list[dict],
    max_tokens_hint: int = 4096,
) -> dict:
    """Build a Mem0-style consolidation prompt — returns prompt + user_text
    + suggested generation params. fi-core does NOT call the LLM; the
    caller executes it with their own credentials.

    Use this BEFORE invoking your LLM to consolidate a user's stored facts.
    After receiving the LLM response, call ``parse_consolidation_result``
    with the raw text + the same facts list to get a validated plan.

    Args:
        facts: List of fact dicts. Each MUST have ``id`` (int), ``fact``
            (str), optional ``category`` (str), and ``updated_at`` (unix
            seconds). Facts with missing required fields are passed
            through to the prompt as-is — the judge can still reason
            about them, but you'll lose age-based conflict resolution.
        max_tokens_hint: Suggested max_tokens for the LLM call. Default
            4096 is enough for ~80 facts; bump for larger sets.

    Returns:
        ``{
            "system_prompt": str,       # send as system prompt
            "user_text":     str,       # send as user message
            "max_tokens":    int,       # max_tokens_hint, echoed back
            "model_hint":    str,       # Haiku-class is plenty
        }``

    Notes:
        - The system prompt is the Mem0-style judge instruction; it
          asks for NOOP/UPDATE/DELETE ops referencing fact ids.
        - Model hint is ``claude-haiku-4-5`` — the judge is structured
          and small-vocab; Sonnet/Opus are overkill.
        - Reference: arxiv 2504.19413 (Mem0 paper).
    """
    return {
        "system_prompt": _CONSOLIDATION_JUDGE_SYSTEM_PROMPT,
        "user_text": _render_facts_as_user_prompt(facts),
        "max_tokens": max_tokens_hint,
        "model_hint": "claude-haiku-4-5",
    }


@mcp.tool()
async def parse_consolidation_result(
    raw_response: str,
    facts: list[dict],
) -> dict:
    """Parse the LLM's raw judge response into a validated op list.

    Pairs with ``build_consolidation_prompt``. Strips markdown fences,
    parses the JSON array, drops malformed ops, and adds implicit NOOPs
    for any facts the judge omitted (so no row is ever silently lost).

    Args:
        raw_response: Verbatim text returned by the LLM. Markdown fences
            (```json ... ```) are tolerated and stripped.
        facts: The SAME facts list passed to ``build_consolidation_prompt``.
            Needed to validate that every input id is referenced in
            exactly one op and to backfill implicit NOOPs.

    Returns:
        ``{
            "ok":      bool,           # True iff parse succeeded
            "ops":     list[dict],     # validated, every fact id covered
            "error":   str | None,     # set when ok=False
            "raw_len": int,            # diagnostic: response size
        }``

        Each op has shape:
        - NOOP/DELETE: ``{"op": "NOOP"|"DELETE", "id": int, "reason": str}``
        - UPDATE: ``{"op": "UPDATE", "merge_ids": list[int], "new_fact": str,
                     "category": str, "reason": str}``
    """
    import json as _json

    text = (raw_response or "").strip()
    if not text:
        return {"ok": False, "ops": [], "error": "empty_response", "raw_len": 0}

    # Strip markdown fence.
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        plan = _json.loads(text)
    except _json.JSONDecodeError as e:
        return {
            "ok": False,
            "ops": [],
            "error": f"json_decode_error: {e}",
            "raw_len": len(raw_response),
        }

    if not isinstance(plan, list):
        return {
            "ok": False,
            "ops": [],
            "error": "expected_array",
            "raw_len": len(raw_response),
        }

    # Validate: drop malformed ops, track which ids the judge addressed.
    valid_ids = {f["id"] for f in facts}
    seen: set[int] = set()
    valid_ops: list[dict] = []
    for op in plan:
        if not isinstance(op, dict) or "op" not in op:
            continue
        kind = op["op"]
        if kind in ("NOOP", "DELETE"):
            fid = op.get("id")
            if fid not in valid_ids or fid in seen:
                continue
            seen.add(fid)
            valid_ops.append(op)
        elif kind == "UPDATE":
            ids = op.get("merge_ids") or []
            new_text = op.get("new_fact")
            if not isinstance(ids, list) or not new_text:
                continue
            ids_int = [
                i for i in ids if isinstance(i, int) and i in valid_ids and i not in seen
            ]
            if not ids_int:
                continue
            seen.update(ids_int)
            op["merge_ids"] = ids_int
            valid_ops.append(op)
        # Unknown op kinds are silently dropped — judge can't invent.

    # Implicit NOOP for any fact id the judge ignored — never silently lose a row.
    for f in facts:
        if f["id"] not in seen:
            valid_ops.append(
                {"op": "NOOP", "id": f["id"], "reason": "implicit (judge omitted)"}
            )

    return {
        "ok": True,
        "ops": valid_ops,
        "error": None,
        "raw_len": len(raw_response),
    }


# ---------------------------------------------------------------------------
# Public contract — explicit per [[mcp-shape-b-canonical]] + the 2026-05-19
# discord-bot integration. Consumers read these to wire up runtime + auto-
# inject the tool list into persona prompts.
# ---------------------------------------------------------------------------

MCP_SERVER_NAME = "fi-core-persona"

MCP_TOOLS: list[dict[str, str]] = [
    {
        "name": "list_packs",
        "description": "List all built-in pattern packs available on this server.",
    },
    {
        "name": "check_drift",
        "description": "Detect persona drift in text using the listed packs.",
    },
    {
        "name": "sanitize_response",
        "description": "Last-resort: remove sentences containing break-severity matches.",
    },
    {
        "name": "get_reinforcement",
        "description": "Return the reinforcement string suitable for a specific pack.",
    },
    {
        "name": "validate_and_retry_prompt",
        "description": "Atomic loop: validate response, decide retry, return reinforced prompt.",
    },
    {
        "name": "build_consolidation_prompt",
        "description": "Build a Mem0-style judge prompt for user-fact consolidation.",
    },
    {
        "name": "parse_consolidation_result",
        "description": "Parse and validate the judge's JSON response into op list.",
    },
]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
