"""Shared per-persona corpus retrieval — topic RAG, not per-user.

Generalization of the film-only module (2026-07-16): a *corpus* is shared
knowledge keyed by a synthetic namespace (`__corpus_*__`) instead of a real
user_id, declared per persona in `shared/personas/registry.py::corpus_namespace`.
Sources live under `data/corpus/<persona_id>/` and are ingested via
`scripts/ingest_corpus.py`; the per-turn references block is injected through
`persona_core.guidance.guidance_for_turn`, with the header content loaded
from `shared/corpus/headers/<persona_id>.md` by the caller (the gateway), so
this module stays free of any `shared.*` import.

Reuses the same table, embedder and pgvector index as the per-user memory; only
the WHERE-key differs. Sits on the persona-neutral `pg_rag` primitives, so this
module imports nothing from persona packages.
"""

from __future__ import annotations

from typing import Any

import structlog

from persona_core.corpus.pg_rag import connect, embed_query, score_relevance

log = structlog.get_logger()

# Retrieval pulls a wide cosine shortlist and the cross-encoder decides what is
# relevant (`pg_rag.CorpusReranker`): e5 cosines cannot gate on their own.
# Floor measured 2026-11-20 over 21 real queries with 8 candidates: off-topic
# topped at -2.61, and the on-topic queries under -2 had pulled wrong chunks
# anyway. A wrong passage misleads the persona; none just leaves it unaided.
_REF_CANDIDATES = 8
_REF_TOP_K = 3
_REF_MIN_RELEVANCE = -2.0
_REF_MIN_QUERY_LEN = 12  # skip "ok"/"jaja" — not worth an embed call
_REF_MAX_CHARS = 2200  # cap injected context so the turn stays bounded
_TRUNCATE_BACKOFF_CHARS = 80  # how far back a truncation looks for a word boundary


async def query_corpus(
    query: str,
    *,
    namespace: str,
    top_k: int = _REF_TOP_K,
) -> list[dict[str, Any]] | None:
    """Embed `query` and return the top-k closest chunks in a shared `namespace`.

    Same cosine retrieval as `deep_memory.query_user_memory`, but the partition
    key is a synthetic corpus namespace rather than a real user_id, so the result
    is topic knowledge shared across all users.

    Returns None when retrieval could not RUN (embedder or Postgres down) and []
    when it ran and found nothing. The two used to be the same `[]`, so a month
    of dead embeddings read in KQL as a month of off-topic questions.
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
        return [
            {
                "source_type": r["source_type"],
                "source_ref": r["source_ref"],
                "chunk_text": r["chunk_text"],
                "similarity": float(r["similarity"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    except Exception:
        log.exception("deep_memory_corpus_query_failed", namespace=namespace, query_len=len(query))
        return None
    finally:
        await conn.close()


def cite_label(source_ref: str | None) -> str:
    """`source_ref` → the short provenance label shown next to a retrieved passage.

    `source_ref` is `<persona_id>:<slug>` (and for a subfoldered corpus,
    `<persona_id>:<subfolder>-<slug>`). The persona prefix is noise to the model
    — it already knows whose corpus this is — so only the slug is rendered.

    Exists because the retrieval always carried provenance and the prompt threw
    it away: `query_corpus` returns source_ref/source_type/similarity, and the
    block rendered `- <text>` alone, so a passage arrived indistinguishable from
    the persona's own invention. The schema comment has said "source_ref lets the
    agent cite where a recalled chunk came from" since the table was written.
    """
    ref = (source_ref or "").strip()
    slug = ref.split(":", 1)[1].strip() if ":" in ref else ref
    # A ref of "insult:" (prefix, empty slug) used to render `- [] passage` — an
    # empty bracket the docstring above already promised would degrade to
    # "corpus". Contract and code now agree.
    return slug or "corpus"


def _truncate_at_word(line: str, max_chars: int) -> str:
    """Cut `line` to at most `max_chars`, backing off to the last word boundary."""
    cut = line[: max_chars - 1]
    space = cut.rfind(" ")
    if space >= len(cut) - _TRUNCATE_BACKOFF_CHARS and space > 0:
        cut = cut[:space]
    return cut.rstrip() + "…"


def fit_to_budget(lines: list[str], max_chars: int) -> tuple[list[tuple[int, str]], bool]:
    """Pick the lines that fit a char budget, in rank order → (`(index, line)` kept, truncated).

    The best passage ALWAYS goes in: if it alone exceeds the budget it is
    truncated at a word boundary instead of dropped. A later line that does not
    fit is skipped, not a stop — a shorter one further down may still fit.

    Exists because the loop used to `break` on the first line over budget: when
    that was the TOP hit, the block came out empty and the function returned
    None with no log event — the corpus was queried, cleared the floor, and the
    persona got nothing (Frugívoro's pregnancy/cardiometabolic turns, 2026-10-03:
    top passages of 2255 to 2589 chars against a 2200 cap; 82 of 893 chunks in
    `__corpus_vegan__` are over it). Shared with `deep_memory.build_user_memory_block`,
    which carried the same loop.
    """
    kept: list[tuple[int, str]] = []
    total = 0
    truncated = False
    for i, line in enumerate(lines):
        if total + len(line) <= max_chars:
            kept.append((i, line))
            total += len(line)
        elif not kept:
            short = _truncate_at_word(line, max_chars)
            kept.append((i, short))
            total += len(short)
            truncated = True
    return kept, truncated


async def build_references_block(query: str | None, *, namespace: str, header: str) -> str | None:
    """Retrieve relevant corpus chunks and format them for prompt injection.

    One implementation for every persona corpus so the similarity/length gating
    lives in ONE place. Returns a labeled, length-capped block or None when the
    query is trivial, retrieval fails, or nothing clears the similarity floor.
    Best-effort: callers wrap this in try/except and a failure here NEVER breaks
    the turn.
    """
    q = (query or "").strip()
    if len(q) < _REF_MIN_QUERY_LEN or not namespace or not header.strip():
        return None
    hits = await query_corpus(q, namespace=namespace, top_k=_REF_CANDIDATES)
    if hits is None:
        log.warning("deep_memory_corpus_unavailable", namespace=namespace)
        return None
    if not hits:
        log.info(
            "deep_memory_corpus_no_hits", namespace=namespace, queried=0, top_relevance=None, floor=_REF_MIN_RELEVANCE
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
    relevant = [h for h in ranked if h["relevance"] >= _REF_MIN_RELEVANCE][:_REF_TOP_K]
    if not relevant:
        log.info(
            "deep_memory_corpus_no_hits",
            namespace=namespace,
            queried=len(hits),
            top_relevance=round(ranked[0]["relevance"], 3),
            floor=_REF_MIN_RELEVANCE,
        )
        return None

    kept, truncated = fit_to_budget(
        [f"- [{cite_label(h.get('source_ref'))}] {h['chunk_text'].strip()}" for h in relevant],
        _REF_MAX_CHARS,
    )

    log.info(
        "deep_memory_corpus_refs_built",
        namespace=namespace,
        hits=len(kept),
        sources=[cite_label(relevant[i].get("source_ref")) for i, _ in kept],
        top_relevance=round(relevant[0]["relevance"], 3),
        low_relevance=round(relevant[kept[-1][0]]["relevance"], 3),
        top_similarity=round(relevant[0].get("similarity", 0.0), 3),
        dropped_below_floor=sum(1 for h in ranked if h["relevance"] < _REF_MIN_RELEVANCE),
        dropped_over_budget=len(relevant) - len(kept),
        truncated=truncated,
    )
    return header.strip() + "\n" + "\n".join(line for _, line in kept)
