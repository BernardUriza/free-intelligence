"""Voice lane: real human lines a persona reads for register, never for facts.

The topical corpus (`references`) cannot carry style. Its cross-encoder gate
keeps only passages that answer the question, so a vulgar exchange about
anything else never clears the floor. This lane skips the reranker on purpose.

Selection follows the evidence gathered 2026-11-20. Random demos beat or tie
similarity-retrieved ones for persona dialogue, and demos too close to the
query get copied verbatim (Pu et al. 2024, arXiv 2402.09954). So the lane draws
a random handful and drops the ones most similar to the ask before keeping
`_STYLE_TOP_K`.
"""

from __future__ import annotations

import structlog

from persona_core.corpus.pg_rag import connect, embed_query

log = structlog.get_logger()

_STYLE_DRAW = 12
_STYLE_DROP_MOST_SIMILAR = 3
_STYLE_TOP_K = 4
_STYLE_MIN_QUERY_LEN = 2


async def draw_style_lines(query: str, *, namespace: str) -> list[dict] | None:
    """A random draw from the pool minus the lines closest to `query`.

    None when the lane could not run (embedder or Postgres down); [] when the
    pool is empty.
    """
    vec = await embed_query(query)
    if vec is None:
        return None
    conn = await connect()
    if conn is None:
        return None
    try:
        rows = await conn.fetch(
            """
            SELECT id, chunk_text, 1 - (embedding <=> $1) AS similarity
            FROM deep_memory_chunks
            WHERE user_id = $2 AND embedding IS NOT NULL
            ORDER BY random()
            LIMIT $3
            """,
            vec,
            namespace,
            _STYLE_DRAW,
        )
    except Exception:
        log.exception("style_pool_query_failed", namespace=namespace)
        return None
    finally:
        await conn.close()
    drawn = [{"id": r["id"], "text": r["chunk_text"], "similarity": float(r["similarity"])} for r in rows]
    by_similarity = sorted(drawn, key=lambda d: d["similarity"], reverse=True)
    too_close = {d["id"] for d in by_similarity[:_STYLE_DROP_MOST_SIMILAR]} if len(drawn) > _STYLE_TOP_K else set()
    return [d for d in drawn if d["id"] not in too_close][:_STYLE_TOP_K]


async def build_style_block(query: str | None, *, namespace: str, header: str) -> str | None:
    """The `<voice_examples>` block for this turn, or None."""
    if not query or len(query.strip()) < _STYLE_MIN_QUERY_LEN:
        return None
    lines = await draw_style_lines(query, namespace=namespace)
    if lines is None:
        log.warning("style_lane_unavailable", namespace=namespace)
        return None
    if not lines:
        log.info("style_pool_empty", namespace=namespace)
        return None
    log.info("style_exemplars_used", namespace=namespace, ids=[d["id"] for d in lines])
    examples = "\n".join(f"<example>{d['text'].strip()}</example>" for d in lines)
    return f"{header.strip()}\n<voice_examples>\n{examples}\n</voice_examples>"
