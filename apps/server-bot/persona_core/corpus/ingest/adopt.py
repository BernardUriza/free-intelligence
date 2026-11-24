"""One-time copy of a namespace out of `deep_memory_chunks`, vectors included.

It keeps what has no local source (the film books) and lets readers move before
any re-embed. Adopted documents carry no fingerprint, so a `plan` replaces each
one its manifest declares. Reads the old table; never changes it.
"""

from __future__ import annotations

import asyncpg
from fi_core.sql import affected_rows

from persona_core.corpus.pg_rag import CORPUS_TABLE_PREFIX

_DOCUMENTS = f"""
INSERT INTO {CORPUS_TABLE_PREFIX}_documents
    (document_id, namespace, content, status, created_at, indexed_at, attributes)
SELECT source_ref, user_id, '', 'indexed', min(created_at), now(), '{{"adopted_from": "deep_memory_chunks"}}'::jsonb
FROM deep_memory_chunks
WHERE user_id = $1 AND embedding IS NOT NULL
GROUP BY user_id, source_ref
"""  # noqa: S608  # nosec B608 — the prefix is a module constant

_CHUNKS = f"""
INSERT INTO {CORPUS_TABLE_PREFIX}_chunks
    (chunk_id, document_id, namespace, text, source_type, source_ref, embedding, created_at)
SELECT 'adopted_' || id, source_ref, user_id, chunk_text, source_type, source_ref, embedding, created_at
FROM deep_memory_chunks
WHERE user_id = $1 AND embedding IS NOT NULL
"""  # noqa: S608  # nosec B608 — the prefix is a module constant


async def adopt_legacy_chunks(dsn: str, namespace: str) -> int:
    """Copy `namespace` into empty corpus tables; refuses one that already has documents."""
    conn = await asyncpg.connect(dsn)
    try:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(hashtext($1))", f"{CORPUS_TABLE_PREFIX}\x1f{namespace}")
            if await conn.fetchval(
                f"SELECT count(*) FROM {CORPUS_TABLE_PREFIX}_documents WHERE namespace = $1",  # noqa: S608  # nosec B608
                namespace,
            ):
                raise RuntimeError(f"{namespace} already has documents; adopt runs once")
            await conn.execute(_DOCUMENTS, namespace)
            return affected_rows(await conn.execute(_CHUNKS, namespace))
    finally:
        await conn.close()
