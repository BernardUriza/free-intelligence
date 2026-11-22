"""Voice lane: real human lines a persona reads for register, never for facts.

It skips the reranker on purpose (a vulgar line about anything else never clears
a topical floor); draw sizes and the anti-copy drop live in `rules.yml`.
"""

from __future__ import annotations

import structlog

from persona_core.corpus.pg_rag import connect, embed_query
from persona_core.corpus.rules import load_rules

log = structlog.get_logger()


async def draw_style_lines(query: str, *, namespace: str) -> list[dict] | None:
    """A random draw from the pool minus the lines closest to `query`: None if it could not run."""
    rules = load_rules().voice
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
            rules.draw,
        )
    except Exception:
        log.exception("style_pool_query_failed", namespace=namespace)
        return None
    finally:
        await conn.close()
    drawn = [{"id": r["id"], "text": r["chunk_text"], "similarity": float(r["similarity"])} for r in rows]
    by_similarity = sorted(drawn, key=lambda d: d["similarity"], reverse=True)
    too_close = {d["id"] for d in by_similarity[: rules.drop_most_similar]} if len(drawn) > rules.top_k else set()
    return [d for d in drawn if d["id"] not in too_close][: rules.top_k]


async def build_style_block(query: str | None, *, namespace: str, header: str) -> str | None:
    """The `<voice_examples>` block for this turn, or None."""
    if not query or len(query.strip()) < load_rules().voice.min_query_chars:
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
