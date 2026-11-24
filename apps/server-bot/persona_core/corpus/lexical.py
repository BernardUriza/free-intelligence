"""The lexical arm of the corpus: one in-memory BM25 index per namespace.

Rebuilt when the namespace changes: the `(count, max id)` stamp is read on every
query, so an ingest is visible on the next turn without a restart. That holds
because chunks are only ever inserted or deleted, never updated in place.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import asyncpg
from fi_core.rag import Bm25Index


@dataclass(frozen=True)
class _Entry:
    stamp: tuple[int, int | None]
    rows: list[dict[str, Any]]
    index: Bm25Index


_cache: dict[str, _Entry] = {}
_building = asyncio.Lock()


async def _entry(conn: asyncpg.Connection, namespace: str) -> _Entry:
    async with _building:
        row = await conn.fetchrow(
            "SELECT count(*) AS n, max(id) AS last FROM deep_memory_chunks WHERE user_id = $1 AND embedding IS NOT NULL",
            namespace,
        )
        stamp = (row["n"], row["last"])
        cached = _cache.get(namespace)
        if cached and cached.stamp == stamp:
            return cached
        records = await conn.fetch(
            """
            SELECT id, source_type, source_ref, chunk_text, created_at
            FROM deep_memory_chunks WHERE user_id = $1 AND embedding IS NOT NULL
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
