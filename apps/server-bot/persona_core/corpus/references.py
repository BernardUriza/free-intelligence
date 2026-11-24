"""Per-persona corpus references: shortlist by meaning and words, gate by cross-encoder, cap by size.

The namespace and the header come from the caller (`shared/corpus/persona_corpus.py`);
every threshold comes from `rules.yml`.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from fi_core.rag import reciprocal_rank_fusion
from fi_core.text import fit_ranked

from persona_core.corpus.lexical import lexical_hits
from persona_core.corpus.pg_rag import connect, embed_query, score_relevance
from persona_core.corpus.rules import load_rules

log = structlog.get_logger()

_TAG_OPENER = re.compile(r"<(?=[/!?]?[A-Za-z_])")


async def query_corpus(query: str, *, namespace: str, top_k: int, fusion_pool: int) -> list[dict[str, Any]] | None:
    """The `top_k` chunks for `query`, by meaning and by words: None if retrieval could not run.

    Each arm ranks the whole namespace and contributes its best `fusion_pool`
    chunks to a reciprocal rank fusion; 0 leaves the cosine alone. A chunk only
    the words found carries `similarity=None`.
    """
    if not query or top_k <= 0:
        return []
    vec = await embed_query(query)
    if vec is None:
        return None
    conn = await connect()
    if conn is None:
        return None
    try:
        rows = await conn.fetch(
            """
            SELECT id, source_type, source_ref, chunk_text, created_at,
                   1 - (embedding <=> $1) AS similarity
            FROM deep_memory_chunks
            WHERE user_id = $2 AND embedding IS NOT NULL
            ORDER BY embedding <=> $1
            LIMIT $3
            """,
            vec,
            namespace,
            max(top_k, fusion_pool),
        )
        dense = [{**dict(r), "similarity": float(r["similarity"])} for r in rows]
        if fusion_pool <= 0:
            return dense[:top_k]
        lexical = await lexical_hits(conn, query, namespace=namespace, limit=fusion_pool)
    except Exception:
        log.exception("deep_memory_corpus_query_failed", namespace=namespace, query_len=len(query))
        return None
    finally:
        await conn.close()
    by_id = {h["id"]: {**h, "similarity": None} for h in lexical} | {h["id"]: h for h in dense}
    fused = reciprocal_rank_fusion([[h["id"] for h in dense], [h["id"] for h in lexical]])
    return [by_id[i] for i in sorted(fused, key=lambda i: -fused[i])[:top_k]]


async def rank_references(query: str, *, namespace: str) -> list[dict[str, Any]] | None:
    """The shortlist with its cross-encoder `relevance`, best first: None if a stage could not run."""
    rules = load_rules().references
    hits = await query_corpus(query, namespace=namespace, top_k=rules.candidates, fusion_pool=rules.fusion_pool)
    if not hits:
        return hits
    scores = await score_relevance(query, [h["chunk_text"] for h in hits])
    if scores is None:
        return None
    ranked = [{**h, "relevance": s} for h, s in zip(hits, scores, strict=True)]
    return sorted(ranked, key=lambda h: h["relevance"], reverse=True)


def above_floor(ranked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The passages that may enter the turn: over the floor, at most `top_k`."""
    rules = load_rules().references
    return [h for h in ranked if h["relevance"] >= rules.min_relevance][: rules.top_k]


def as_data(passage: str) -> str:
    """The passage with every markup opener defused, so it cannot close or open a prompt block."""
    return _TAG_OPENER.sub("\u2039", passage.strip())


def cite_label(source_ref: str | None) -> str:
    """`<persona_id>:<slug>` → `<slug>`, or "corpus" when there is no slug."""
    ref = (source_ref or "").strip()
    slug = ref.split(":", 1)[1].strip() if ":" in ref else ref
    return slug or "corpus"


async def build_references_block(
    query: str | None, *, namespace: str, header: str, min_passages: int = 0
) -> str | None:
    """The references block for this turn, or None.

    `min_passages` keeps that many top-ranked passages even below the floor
    (a corpus of ammunition, not facts); the log then says `forced=True`.
    """
    rules = load_rules().references
    q = (query or "").strip()
    if len(q) < rules.min_query_chars or not namespace or not header.strip():
        return None
    ranked = await rank_references(q, namespace=namespace)
    if ranked is None:
        log.warning("deep_memory_corpus_unavailable", namespace=namespace)
        return None
    relevant = above_floor(ranked)
    forced = not relevant and min_passages > 0
    if forced:
        relevant = ranked[:min_passages]
    if not relevant:
        log.info(
            "deep_memory_corpus_no_hits",
            namespace=namespace,
            queried=len(ranked),
            top_relevance=round(ranked[0]["relevance"], 3) if ranked else None,
            floor=rules.min_relevance,
        )
        return None

    kept, truncated = fit_ranked(
        [f"- [{cite_label(h.get('source_ref'))}] {as_data(h['chunk_text'])}" for h in relevant],
        rules.max_block_chars,
        word_backoff=rules.truncate_backoff_chars,
    )
    log.info(
        "deep_memory_corpus_refs_built",
        namespace=namespace,
        hits=len(kept),
        forced=forced,
        sources=[cite_label(relevant[i].get("source_ref")) for i, _ in kept],
        top_relevance=round(relevant[0]["relevance"], 3),
        low_relevance=round(relevant[kept[-1][0]]["relevance"], 3),
        top_similarity=round(sim, 3) if (sim := relevant[0].get("similarity")) is not None else None,
        dropped_below_floor=sum(1 for h in ranked if h["relevance"] < rules.min_relevance),
        dropped_over_budget=len(relevant) - len(kept),
        truncated=truncated,
    )
    return header.strip() + "\n" + "\n".join(line for _, line in kept)
