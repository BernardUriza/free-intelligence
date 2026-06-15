"""Shared film-theory corpus retrieval — topic RAG, not per-user.

Extracted from `personas/insult/core/deep_memory.py` (Etapa 3 demux físico,
2026-06-15). This is the neutral capability that killed the cross-persona edge:
Insult (`composition.film_references_block`) and ALICE (`alice/cogs/chat.py`)
both retrieve film-theory references here instead of ALICE reaching into the
Insult persona's `deep_memory`.

A *corpus* is shared knowledge keyed by a synthetic namespace instead of a real
user_id. The film-theory books (Braudy & Cohen; The Language and Style of Film
Criticism) are ingested under `FILM_CORPUS_NAMESPACE` via
`scripts/ingest_film_corpus.py` (source_type="manual") and retrieved on any turn
whose topic is film — for ANY user. Reuses the same table, embedder and pgvector
index as the per-user memory; only the WHERE-key differs.

Sits on the persona-neutral `pg_rag` primitives, so this module imports nothing
from `personas.*`.
"""

from __future__ import annotations

from typing import Any

import structlog

from khimeras_shared.corpus.pg_rag import connect, embed_text

log = structlog.get_logger()

FILM_CORPUS_NAMESPACE = "__corpus_film__"

# Tuning for the film-references injection — mirrors the per-user memory knobs
# in deep_memory.py so the two retrieval paths behave consistently.
_FILM_REF_TOP_K = 3
_FILM_REF_MIN_SIMILARITY = 0.30  # cosine sim floor; drop weak hits
_FILM_REF_MIN_QUERY_LEN = 12  # skip "ok"/"jaja" — not worth an embed call
_FILM_REF_MAX_CHARS = 2200  # cap injected context so the turn stays bounded

_FILM_REF_HEADER = (
    "REFERENCIAS DE TEORÍA CINEMATOGRÁFICA (Braudy & Cohen — Film Theory and "
    "Criticism / The Language and Style of Film Criticism). Úsalas como munición "
    "analítica EN TU VOZ — no las cites literal, no las anuncies como fuente, "
    "no las trates como autoridad incuestionable; son herramienta de disección, "
    "no escudo académico:"
)


async def query_corpus(
    query: str,
    *,
    namespace: str = FILM_CORPUS_NAMESPACE,
    top_k: int = _FILM_REF_TOP_K,
) -> list[dict[str, Any]]:
    """Embed `query` and return the top-k closest chunks in a shared `namespace`.

    Same cosine retrieval as `deep_memory.query_user_memory`, but the partition
    key is a synthetic corpus namespace rather than a real user_id, so the result
    is topic knowledge shared across all users. Returns [] on any failure path
    (no PG, no embedding service, empty corpus) — absence of corpus is a valid
    answer, never an error.
    """
    if not query or top_k <= 0:
        return []
    vec = await embed_text(query)
    if vec is None:
        return []
    conn = await connect()
    if conn is None:
        return []
    try:
        rows = await conn.fetch(
            """
            SELECT source_type, source_ref, chunk_text, created_at,
                   1 - (embedding <=> $1) AS similarity
            FROM deep_memory_chunks
            WHERE user_id = $2
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
        return []
    finally:
        await conn.close()


async def build_film_references_block(query: str | None) -> str | None:
    """Retrieve relevant film-theory chunks and format them for prompt injection.

    Shared by Insult (`composition.film_references_block`) and ALICE
    (`alice/cogs/chat.py`) so the header and the similarity/length gating live in
    ONE place. Returns a labeled, length-capped block or None when the query is
    trivial, retrieval fails, or nothing clears the similarity floor. Best-effort:
    callers wrap this in try/except and a failure here NEVER breaks the turn.
    """
    q = (query or "").strip()
    if len(q) < _FILM_REF_MIN_QUERY_LEN:
        return None
    hits = await query_corpus(q, top_k=_FILM_REF_TOP_K)
    relevant = [h for h in hits if h.get("similarity", 0.0) >= _FILM_REF_MIN_SIMILARITY]
    if not relevant:
        return None

    lines: list[str] = []
    total = 0
    for h in relevant:
        line = f"- {h['chunk_text'].strip()}"
        if total + len(line) > _FILM_REF_MAX_CHARS:
            break
        lines.append(line)
        total += len(line)
    if not lines:
        return None

    log.info(
        "deep_memory_film_refs_built",
        hits=len(lines),
        top_similarity=round(relevant[0].get("similarity", 0.0), 3),
    )
    return _FILM_REF_HEADER + "\n" + "\n".join(lines)
