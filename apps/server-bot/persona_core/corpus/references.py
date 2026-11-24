"""Per-persona corpus references: shortlist by cosine, gate by cross-encoder, cap by size.

The namespace and the header come from the caller (`shared/corpus/persona_corpus.py`);
every threshold comes from `rules.yml`.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from fi_core.text import fit_ranked

from persona_core.corpus.pg_rag import connect, embed_query, score_relevance
from persona_core.corpus.rules import load_rules

log = structlog.get_logger()

_TAG_OPENER = re.compile(r"<(?=[/!?]?[A-Za-z_])")


async def query_corpus(query: str, *, namespace: str, top_k: int) -> list[dict[str, Any]] | None:
    """The `top_k` chunks nearest to `query`: None if retrieval could not run, [] if it found nothing."""
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
            SELECT source_type, source_ref, chunk_text, created_at,
                   1 - (embedding <=> $1) AS similarity
            FROM deep_memory_chunks
            WHERE user_id = $2 AND embedding IS NOT NULL
            ORDER BY embedding <=> $1
            LIMIT $3
            """,
            vec,
            namespace,
            top_k,
        )
        return [{**dict(r), "similarity": float(r["similarity"])} for r in rows]
    except Exception:
        log.exception("deep_memory_corpus_query_failed", namespace=namespace, query_len=len(query))
        return None
    finally:
        await conn.close()


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
    hits = await query_corpus(q, namespace=namespace, top_k=rules.candidates)
    if hits is None:
        log.warning("deep_memory_corpus_unavailable", namespace=namespace)
        return None
    if not hits:
        log.info(
            "deep_memory_corpus_no_hits", namespace=namespace, queried=0, top_relevance=None, floor=rules.min_relevance
        )
        return None
    scores = await score_relevance(q, [h["chunk_text"] for h in hits])
    if scores is None:
        log.warning("deep_memory_corpus_unavailable", namespace=namespace, stage="rerank")
        return None
    ranked = sorted(
        ({**h, "relevance": s} for h, s in zip(hits, scores, strict=True)),
        key=lambda h: h["relevance"],
        reverse=True,
    )
    relevant = [h for h in ranked if h["relevance"] >= rules.min_relevance][: rules.top_k]
    forced = not relevant and min_passages > 0
    if forced:
        relevant = ranked[:min_passages]
    if not relevant:
        log.info(
            "deep_memory_corpus_no_hits",
            namespace=namespace,
            queried=len(hits),
            top_relevance=round(ranked[0]["relevance"], 3),
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
        top_similarity=round(relevant[0].get("similarity", 0.0), 3),
        dropped_below_floor=sum(1 for h in ranked if h["relevance"] < rules.min_relevance),
        dropped_over_budget=len(relevant) - len(kept),
        truncated=truncated,
    )
    return header.strip() + "\n" + "\n".join(line for _, line in kept)
