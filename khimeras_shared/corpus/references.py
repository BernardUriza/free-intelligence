"""Shared per-persona corpus retrieval — topic RAG, not per-user.

Generalization of the film-only module (2026-07-16): a *corpus* is shared
knowledge keyed by a synthetic namespace (`__corpus_*__`) instead of a real
user_id, declared per persona in `shared/personas/registry.py::corpus_namespace`.
Sources live under `data/corpus/<persona_id>/` and are ingested via
`scripts/ingest_corpus.py`; the per-turn references block is injected through
`khimeras_shared.guidance.guidance_for_turn`, with the header content loaded
from `shared/corpus/headers/<persona_id>.md` by the caller (the gateway), so
this module stays free of any `shared.*` import.

Reuses the same table, embedder and pgvector index as the per-user memory; only
the WHERE-key differs. Sits on the persona-neutral `pg_rag` primitives, so this
module imports nothing from persona packages.
"""

from __future__ import annotations

from typing import Any

import structlog

from khimeras_shared.corpus.pg_rag import connect, embed_text

log = structlog.get_logger()

# Tuning for the references injection — mirrors the per-user memory knobs in
# deep_memory.py so the two retrieval paths behave consistently.
_REF_TOP_K = 3
# ada-002 es anisotrópico: sus cosenos viven ~[0.65, 0.95] aun entre textos SIN
# relación (media ~0.85 para relacionados; <0.4 prácticamente no existe). Un
# floor de 0.30 era un NO-OP: jamás filtró nada y todo top-k entraba al turno —
# el failure mode exacto de RAG para role-play (chunks irrelevantes distraen al
# personaje). 0.78 corta lo claramente-ajeno; calibrar con la telemetría
# top/low_similarity de `deep_memory_corpus_refs_built` (2026-07-16).
_REF_MIN_SIMILARITY = 0.78
_REF_MIN_QUERY_LEN = 12  # skip "ok"/"jaja" — not worth an embed call
_REF_MAX_CHARS = 2200  # cap injected context so the turn stays bounded


async def query_corpus(
    query: str,
    *,
    namespace: str,
    top_k: int = _REF_TOP_K,
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
    hits = await query_corpus(q, namespace=namespace, top_k=_REF_TOP_K)
    relevant = [h for h in hits if h.get("similarity", 0.0) >= _REF_MIN_SIMILARITY]
    if not relevant:
        return None

    lines: list[str] = []
    total = 0
    for h in relevant:
        line = f"- [{cite_label(h.get('source_ref'))}] {h['chunk_text'].strip()}"
        if total + len(line) > _REF_MAX_CHARS:
            break
        lines.append(line)
        total += len(line)
    if not lines:
        return None

    log.info(
        "deep_memory_corpus_refs_built",
        namespace=namespace,
        hits=len(lines),
        top_similarity=round(relevant[0].get("similarity", 0.0), 3),
        low_similarity=round(relevant[len(lines) - 1].get("similarity", 0.0), 3),
        dropped_below_floor=len(hits) - len(relevant),
    )
    return header.strip() + "\n" + "\n".join(lines)
