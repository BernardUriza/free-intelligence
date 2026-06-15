"""Deterministic near-miss fold — PR-3 Tier A (the SAFE half).

The fact-consolidation problem has two tiers, and conflating them is what shot
Alex on 2026-06-03:

  Tier A (here): collapse facts that are the SAME statement written with a
    different SURFACE form only — a comma, an accent, a trailing period, a
    thousands separator, different casing or spacing. This is orthographic
    deduplication, not a judgment about what to forget.

  Tier B (memory_consolidator.py, FROZEN): ask an LLM to merge semantically
    overlapping facts ("Vive en México" + "Está viviendo en CDMX"). That tier
    requires the model to decide which information is redundant — and a small
    model over-grouped substantive disclosures and buried a user's entire
    trauma history. It stays capped at CONSOLIDATION_MAX_DESTROY_FRACTION = 0.0
    until a human-reviewed redesign.

THE SAFETY PROOF (airtight by construction).
  `norm_fact_strong` NEVER removes a word. It only erases surface noise:
  case, whitespace, accents, punctuation, and thousands separators. Every
  content token — every noun, verb, number, and named entity — survives into
  the fold key. Therefore two facts can share a key ONLY if they are word-for-
  word identical modulo orthography, which means they cannot differ in meaning.

  This is deliberately STRICTER than an earlier draft that also dropped
  determiners/possessives. That draft could merge "su dinero" with "mi dinero"
  (whose money?) or the article-vs-object-pronoun "la" — i.e. it could destroy
  distinct information, the exact Alex failure in miniature. Determiner-
  insertion variants ("espera una transferencia" vs "espera transferencia")
  are NOT folded here on purpose: they require judgment and belong to Tier B.
  Under-folding is safe; over-folding forgets.

  Cosine similarity is also rejected as a fold signal: "le prestó 3,500 pesos"
  and "le prestó 5,000 pesos" are ~0.98 cosine-similar (one digit barely moves
  the embedding) yet are different facts. This module touches no embeddings.

Output is a plan in the exact shape FactsRepository.apply_consolidation_plan
already consumes (NOOP/DELETE ops), so the existing transactional + audited
apply path is reused verbatim — this module only DECIDES the fold, never the DB.
"""

from __future__ import annotations

import re
import unicodedata

from personas.insult.core.facts import norm_fact

# Collapse a separator only when it sits between a digit and a group of EXACTLY
# three digits at a word/number boundary — i.e. a real thousands separator.
# "3,500" / "3.500" -> "3500", and "1,234,567" -> "1234567" (both seps match,
# non-overlapping). Decimals are preserved: "3,5" / "3.5" / "1,50" never match
# (fewer than 3 trailing digits), so "3,5 litros" stays distinct from "35".
_THOUSANDS_SEP = re.compile(r"(?<=\d)[.,](?=\d{3}(?:\D|$))")

# Any remaining punctuation becomes a space. Word chars (incl. digits) survive.
_PUNCT = re.compile(r"[^\w\s]")


def norm_fact_strong(s: str) -> str:
    """Orthographic dedup key: stronger than `norm_fact` but WORD-PRESERVING.

    Built on top of `norm_fact` (PR-1's lowercase + whitespace-collapse), then
    folds accents, punctuation, and thousands separators. It removes no words,
    so anything `norm_fact` already considers equal stays equal here and the
    safety proof in the module docstring holds.
    """
    s = norm_fact(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = _THOUSANDS_SEP.sub("", s)
    s = _PUNCT.sub(" ", s)
    return " ".join(s.split())


def _survivor(cluster: list[dict]) -> dict:
    """Pick the fact to keep from a fold cluster: the longest text (richest
    phrasing), tie-broken by highest id (newest)."""
    return max(cluster, key=lambda f: (len(f.get("fact", "")), f.get("id", 0)))


def build_near_miss_plan(facts: list[dict]) -> list[dict]:
    """Group `facts` by their orthographic key and emit a fold plan.

    For every group with more than one member: NOOP the survivor, DELETE the
    rest. Groups of one are left untouched (no op emitted — nothing to apply).

    Each fact dict needs `id` and `fact`. The returned ops match the shape
    consumed by FactsRepository.apply_consolidation_plan:
        {"op": "NOOP",   "id": int, "reason": str}
        {"op": "DELETE", "id": int, "reason": str}
    """
    clusters: dict[str, list[dict]] = {}
    for f in facts:
        text = f.get("fact", "")
        if not text:
            continue
        clusters.setdefault(norm_fact_strong(text), []).append(f)

    plan: list[dict] = []
    for cluster in clusters.values():
        if len(cluster) < 2:
            continue
        keep = _survivor(cluster)
        plan.append(
            {
                "op": "NOOP",
                "id": keep["id"],
                "reason": f"near_miss_survivor of {len(cluster)} orthographic variants",
            }
        )
        for f in cluster:
            if f["id"] == keep["id"]:
                continue
            plan.append(
                {
                    "op": "DELETE",
                    "id": f["id"],
                    "reason": "near_miss_orthographic_variant",
                }
            )
    return plan
