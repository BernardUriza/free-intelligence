"""The corpus's one write path — a document's version and its index, together or not at all (#55).

`corpus_versions` keeps every text a document had; `aire_corpus_chunk` indexes the
newest. They were two transactions at first, and the gap between them was a real
defect: a version that committed while its reindex failed (a statement timeout on
a long document, a restart) left the index on the OLD text, and the retry saw an
unchanged text with chunks present and reported success. Search kept answering
sentences the document no longer said, forever. So:

- the version row and the chunks are written in ONE transaction;
- a document's writes are serialized by `pg_advisory_xact_lock` on its key, and a
  whole-corpus delete takes that corpus's lock exclusively while a put holds it
  shared, so a delete cannot interleave with a put of one of its documents;
- the index is "current" only when every chunk carries the sha256 of the newest
  version — a chunk table that merely has rows proves nothing.
"""

from __future__ import annotations

from typing import Any

from . import corpus_schema, corpus_versions, db
from .chunking import chunk, fold
from .corpus_schema import TABLE

STATEMENT_TIMEOUT_MS = 5_000
_DOC_LOCK = "SELECT pg_advisory_xact_lock(hashtext($1 || chr(31) || $2 || chr(31) || $3))"
_CORPUS_LOCK = "SELECT pg_advisory_xact_lock{}(hashtext($1 || chr(31) || $2))"


async def put(owner: str, corpus_id: str, doc_id: str, text: str) -> dict:
    """Store `text` as the document's newest version and make the index match it.
    Reports the version it landed as and whether the text changed."""
    await corpus_schema.ensure()
    await corpus_versions.ensure()
    sha = corpus_versions.digest(text)
    async with db.acquire(statement_timeout_ms=STATEMENT_TIMEOUT_MS) as conn:
        await conn.execute(_CORPUS_LOCK.format("_shared"), owner, corpus_id)
        await conn.execute(_DOC_LOCK, owner, corpus_id, doc_id)
        meta, appended = await corpus_versions.record(conn, owner, corpus_id, doc_id, text)
        chunks = (await _current(conn, owner, corpus_id, doc_id, sha)
                  or await _reindex(conn, owner, corpus_id, doc_id, text, sha))
    return {"chunks": chunks, "version": meta["version"], "sha256": meta["sha256"], "changed": appended}


async def _current(conn: Any, owner: str, corpus_id: str, doc_id: str, sha: str) -> int:
    """How many chunks the index holds for this document IF every one was cut from
    `sha`; 0 when it is empty or holds any other text."""
    row = await conn.fetchrow(
        f"SELECT count(*) AS n, bool_and(sha256 = $4) AS fresh FROM {TABLE}"
        " WHERE owner=$1 AND corpus_id=$2 AND doc_id=$3", owner, corpus_id, doc_id, sha)
    return int(row["n"]) if row["fresh"] else 0


async def _reindex(conn: Any, owner: str, corpus_id: str, doc_id: str, text: str, sha: str) -> int:
    chunks = chunk(text)
    await conn.execute(f"DELETE FROM {TABLE} WHERE owner=$1 AND corpus_id=$2 AND doc_id=$3",
                       owner, corpus_id, doc_id)
    await conn.executemany(
        f"INSERT INTO {TABLE} (owner, corpus_id, doc_id, ord, body, norm, sha256)"
        " VALUES ($1,$2,$3,$4,$5,$6,$7)",
        [(owner, corpus_id, doc_id, i, body, fold(body), sha) for i, body in enumerate(chunks)])
    return len(chunks)


async def drop(owner: str, corpus_id: str, doc_id: str | None = None) -> int:
    """Delete one document, or the whole corpus when `doc_id` is None: its chunks
    and a tombstone, in one transaction. Returns the chunk rows removed, so a
    delete that matched nothing can say so instead of reporting a success the
    caller cannot distinguish from a typo."""
    await corpus_schema.ensure()
    await corpus_versions.ensure()
    sql = f"DELETE FROM {TABLE} WHERE owner=$1 AND corpus_id=$2"
    args: tuple = (owner, corpus_id)
    async with db.acquire(statement_timeout_ms=STATEMENT_TIMEOUT_MS) as conn:
        if doc_id is None:
            await conn.execute(_CORPUS_LOCK.format(""), owner, corpus_id)
        else:
            await conn.execute(_CORPUS_LOCK.format("_shared"), owner, corpus_id)
            await conn.execute(_DOC_LOCK, owner, corpus_id, doc_id)
            sql, args = sql + " AND doc_id=$3", (owner, corpus_id, doc_id)
        tag = await conn.execute(sql, *args)
        await corpus_versions.tombstone(conn, owner, corpus_id, doc_id)
    return int(tag.rsplit(" ", 1)[-1] or 0)
