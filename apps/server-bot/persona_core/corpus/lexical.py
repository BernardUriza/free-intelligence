"""The lexical arm of the corpus: one in-memory BM25 index per namespace.

Rebuilt when the namespace changes: the `(documents, last indexed_at)` stamp is
read on every query, so a sync is visible on the next turn without a restart. A
replaced document moves `indexed_at`; a deleted one moves the count.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import asyncpg
from fi_core.rag import Bm25Index


@dataclass(frozen=True)
class _Entry:
    stamp: tuple[int, datetime | None]
    rows: list[dict[str, Any]]
    index: Bm25Index


_cache: dict[str, _Entry] = {}
_building = asyncio.Lock()


async def _entry(conn: asyncpg.Connection, namespace: str) -> _Entry:
    async with _building:
        row = await conn.fetchrow(
            "SELECT count(*) AS n, max(indexed_at) AS last FROM corpus_documents WHERE namespace = $1",
            namespace,
        )
        stamp = (row["n"], row["last"])
        cached = _cache.get(namespace)
        if cached and cached.stamp == stamp:
            return cached
        records = await conn.fetch(
            """
            SELECT chunk_id AS id, source_type, source_ref, text AS chunk_text, created_at
            FROM corpus_chunks WHERE namespace = $1
            """,
            namespace,
        )
        rows = [dict(r) for r in records]
        index = await asyncio.to_thread(Bm25Index, [r["chunk_text"] for r in rows])
        entry = _Entry(stamp, rows, index)
        _cache[namespace] = entry
        return entry


async def lexical_hits(conn: asyncpg.Connection, query: str, *, namespace: str, limit: int) -> list[dict[str, Any]]:
    """The `limit` chunks of `namespace` that best match the words of `query`, best first."""
    entry = await _entry(conn, namespace)
    return [entry.rows[i] for i in entry.index.rank(query, limit=limit)]
