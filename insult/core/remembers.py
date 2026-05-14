"""Fact-learning marker parser — `[REMEMBER:]` extraction and stripping.

Mirrors the `[REACT:]` pipeline in `core/reactions.py`. The persona emits
`[REMEMBER: <one-clause fact>]` markers when something durable about the
user surfaces in a conversation. This module:

- `parse_remembers(text)`: extract the fact clauses
- `strip_remembers(text)`: remove the markers before sending to Discord
- `persist_remembers(memory, user_id, user_name, facts)`: write them to
  the user_facts table (analogous to background fact extraction, but
  driven by the model in-band instead of a separate Haiku call)

The marker is the in-band substitute for the legacy `core/facts.py`
extraction pass. When the agent runner is the canonical LLM path and
the legacy LLMClient is disabled, this is how new facts enter Postgres.
"""

from __future__ import annotations

import re

import structlog

log = structlog.get_logger()

REMEMBER_PATTERN = re.compile(r"\[REMEMBER:([^\]]*)\]", re.IGNORECASE)
MAX_FACTS_PER_TURN = 2
MAX_FACT_LEN = 200  # generous cap; persona says ~140 but the marker may include qualifiers


def parse_remembers(response: str) -> list[str]:
    """Extract fact clauses from `[REMEMBER:...]` markers.

    Returns at most `MAX_FACTS_PER_TURN` cleaned clauses. Empty list when
    no marker present or all markers are malformed.
    """
    if not response or "[REMEMBER:" not in response.upper():
        return []
    facts: list[str] = []
    for match in REMEMBER_PATTERN.finditer(response):
        clause = (match.group(1) or "").strip()
        if not clause:
            continue
        if len(clause) > MAX_FACT_LEN:
            clause = clause[:MAX_FACT_LEN].rstrip() + "…"
        facts.append(clause)
        if len(facts) >= MAX_FACTS_PER_TURN:
            break
    return facts


def strip_remembers(response: str) -> str:
    """Remove all `[REMEMBER:...]` markers from the response text.

    Same conservative cleanup as `strip_reactions`: removes the marker
    and collapses any double-spaces / leading newlines introduced by the
    removal.
    """
    if not response:
        return response
    cleaned = REMEMBER_PATTERN.sub("", response)
    # Collapse the double-space and double-newline holes that the
    # removal often leaves (e.g. "ok. [REMEMBER:...] gracias" ->
    # "ok.  gracias"). Conservative: only multi-space and multi-newline.
    cleaned = re.sub(r"  +", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


async def persist_remembers(memory, user_id: str, facts: list[str]) -> int:
    """Write each `[REMEMBER:]` clause as a user fact (source='agent').

    Returns the count of facts actually persisted. Failures are logged
    but don't raise — fact learning is best-effort, never blocks the
    user-visible turn.
    """
    if not facts:
        return 0
    saved = 0
    for clause in facts:
        try:
            await memory.add_remember_fact(user_id, clause)
            saved += 1
        except Exception:
            log.exception("remember_persist_failed", user_id=user_id, fact_preview=clause[:80])
    if saved:
        log.info("remember_persist_complete", user_id=user_id, count=saved)
    return saved
