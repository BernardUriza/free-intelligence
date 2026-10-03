"""Fact-learning marker parser — `[REMEMBER:]` extraction, stripping, persist.

Shared text util (like `persona_core/reactions.py` / `research_marker.py`):
BOTH the plumbing and the gateway parse this marker off a runner response, so it
lives in `persona_core` — never in a persona package the gateway may not
import.

The persona emits `[REMEMBER: <one-clause fact>]` when something durable about
the user surfaces in a conversation. This module:

- `parse_remembers(text)`: extract the fact clauses (one or two per turn)
- `strip_remembers(text)`: remove the markers before sending to Discord
- `persist_remembers(memory, user_id, facts)`: write each clause via the
  ADD-only `memory.add_remember_fact` (source='agent'), a pure INSERT that never
  snapshot-replaces — so it can never hard-delete an existing fact.

The marker is the in-band substitute for the automatic Haiku extraction pass
(`persona_core.facts`). The agent runner is the canonical LLM path; this
marker is how model-chosen facts enter Postgres straight from the turn.
"""

from __future__ import annotations

import re

import structlog

log = structlog.get_logger()

REMEMBER_PATTERN = re.compile(r"\[REMEMBER:([^\]]*)\]", re.IGNORECASE)
MAX_FACTS_PER_TURN = 2
MAX_FACT_LEN = 200  # generous cap; persona says ~140 but the marker may include qualifiers

__all__ = [
    "MAX_FACTS_PER_TURN",
    "MAX_FACT_LEN",
    "REMEMBER_PATTERN",
    "parse_remembers",
    "persist_remembers",
    "strip_remembers",
]


def parse_remembers(response: str) -> list[str]:
    """Extract fact clauses from `[REMEMBER:...]` markers.

    Returns at most `MAX_FACTS_PER_TURN` cleaned clauses. Empty list when no
    marker present or all markers are malformed.
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

    Same conservative cleanup as `strip_reactions`: removes the marker and
    collapses the double-space / double-newline holes the removal leaves.
    """
    if not response:
        return response
    cleaned = REMEMBER_PATTERN.sub("", response)
    cleaned = re.sub(r"  +", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


async def persist_remembers(memory, user_id: str, facts: list[str]) -> int:
    """Write each `[REMEMBER:]` clause as a user fact (source='agent').

    Uses `memory.add_remember_fact`, a pure INSERT — the ADD-only path for
    model-chosen facts. It never snapshot-replaces, so it cannot hard-delete an
    existing fact (the P0 that `save_facts(subset)` re-introduces). Returns the
    count of facts actually persisted. Failures are logged but never raise —
    fact learning is best-effort and never blocks the user-visible turn.
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
