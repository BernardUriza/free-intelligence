"""User invariants — the facts that must ride EVERY turn, outside the ranking.

The 2026-07-23 failure that created this module: asked about concerts, the
persona offered Bernard a Christian-rock band. He is an atheist. The postmortem
found two separate holes, and only one of them was the missing fact:

1. No fact in the store said he is an atheist (4,123 facts, zero on it) — the
   extractor had never been told that a worldview is worth keeping.
2. Even had it existed, it could not have arrived. The ONLY automatic fact
   channel into a turn is `RELEVANT_FACTS_LIMIT = 8` hits ranked by semantic
   similarity to the ask. Nothing about atheism resembles "when does this band
   play live", so the invariant loses the ranking against trivia about music —
   forever, by construction.

The fix is not a bigger top-N. Facts like *atheist*, *vegan*, *allergic to X*,
*does not drive*, *no contact with their father* are not trivia competing for
prompt space: they are **restrictions on what may be said at all**. They get a
reserved `category` (`constraint`) and this dedicated lane, which:

- rides on `behavioral_guidance` — the channel that already reaches the model on
  EVERY turn, so there is no new wire and no new failure mode;
- is placed FIRST in that guidance, so the 16,000-char truncation eats the
  preset prose before it ever eats an invariant;
- derives from the facts `guidance_for_turn` ALREADY loaded for the vulnerability
  score — zero extra queries per turn.

`category` is reused deliberately (it is already a free-text column every writer
sets) instead of a new column: no `principal_facts` migration, and the tools that
read facts show the tag for free.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from khimeras_shared.prompts import PromptCache, load_prompt

log = structlog.get_logger()

CONSTRAINT_CATEGORY = "constraint"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts_md"

# A ceiling, not a ranking: invariants are a handful by nature, and a store that
# somehow accumulates hundreds must not eat the whole guidance budget. Crossing
# it is logged as the data problem it is, never silently trimmed.
MAX_CONSTRAINTS = 40

_CACHE: PromptCache = {}


def _dedupe_key(text: str) -> str:
    """Normalized key for near-identical restatements of the same invariant."""
    lowered = text.casefold()
    stripped = "".join(ch for ch in lowered if ch.isalnum() or ch.isspace())
    return " ".join(stripped.split())


def select_constraints(user_facts: list[dict] | None) -> list[str]:
    """The user's invariant facts, deduped, capped at `MAX_CONSTRAINTS`.

    Reads the same fact dicts the guardian already holds — no store access.

    Dedup is not cosmetic. The fact store grows ADD-only across personas and
    re-extractions, so ONE invariant accumulates restatements: Bernard's "es
    vegano" exists 14 times in 14 wordings. Undeduped, the block would spend its
    whole budget repeating one restriction and crowd out the others — the same
    signal-dilution the top-8 ranking already caused. Keeps the LONGEST wording
    of each (the one carrying the qualifiers), then restores store order.
    """
    if not user_facts:
        return []
    picked = [
        text
        for fact in user_facts
        if isinstance(fact, dict)
        and (fact.get("category") or "").strip().lower() == CONSTRAINT_CATEGORY
        and (text := (fact.get("fact") or "").strip())
    ]
    best: dict[str, tuple[int, str]] = {}
    for position, text in enumerate(picked):
        key = _dedupe_key(text)
        current = best.get(key)
        if current is None or len(text) > len(current[1]):
            best[key] = (current[0] if current else position, text)

    # Then collapse the SUBSUMED ones: "Es vegano" is contained in "Es vegano
    # absolutista y abolicionista", so keeping both spends two lines on one
    # restriction and loses nothing when the shorter goes. Containment only —
    # never similarity, which could silently merge two different invariants.
    kept: list[tuple[int, str]] = []
    for key, (position, text) in best.items():
        if any(key != other and key in other for other in best):
            continue
        kept.append((position, text))
    deduped = [text for _, text in sorted(kept, key=lambda pair: pair[0])]
    if len(deduped) < len(picked):
        log.info("constraints_deduped", raw=len(picked), unique=len(deduped))
    if len(deduped) > MAX_CONSTRAINTS:
        log.warning("constraints_capped", total=len(deduped), cap=MAX_CONSTRAINTS)
        deduped = deduped[:MAX_CONSTRAINTS]
    return deduped


def build_constraints_block(user_facts: list[dict] | None) -> str | None:
    """Render the invariants block for the turn's guidance, or None if there are
    none. Any fault degrades to None: a missing block is a normal turn."""
    try:
        constraints = select_constraints(user_facts)
        if not constraints:
            return None
        header = load_prompt(PROMPTS_DIR, "user_constraints", _CACHE)
        body = "\n".join(f"- {c}" for c in constraints)
        return f"{header}\n\n{body}"
    except Exception:
        log.exception("constraints_block_failed")
        return None


def is_constraint(fact: Any) -> bool:
    """Whether one fact dict carries the reserved invariant category."""
    return isinstance(fact, dict) and (fact.get("category") or "").strip().lower() == CONSTRAINT_CATEGORY


__all__ = [
    "CONSTRAINT_CATEGORY",
    "MAX_CONSTRAINTS",
    "build_constraints_block",
    "is_constraint",
    "select_constraints",
]
