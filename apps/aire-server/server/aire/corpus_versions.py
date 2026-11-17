"""Every version a corpus document ever had — the document's history, append-only.

`aire_corpus_chunk` is an INDEX: `ingest` deletes a document's chunks and writes
new ones, and chunking strips the blank lines it splits on, so neither the old
text nor the exact new one can be read back from it. A consumer that keeps its
research here (videopipe's expedientes, 2026-11-16) needs both: the exact bytes
it stored, and what the document said before the last edit. That is the
[[log-is-the-truth]] shape — a correction appends, nothing is mutated — so each
write is a new row, "current" is the newest, and a delete is a tombstone row.

A write whose text hashes the same as the newest version appends nothing: a
re-push of an unchanged tree must not grow the table or re-chunk the document.

Created as role `aire`, so the reader's default grant covers it
([[write-only-daemon]]). Reading it back is the consumer reading rows it owns,
the widened criterion that rule records for the corpus door (#47, #55).
"""

from __future__ import annotations

import asyncio
import hashlib

from . import db

TABLE = "aire_corpus_version"
STATEMENT_TIMEOUT_MS = 5_000
DDL = (
    f"CREATE TABLE IF NOT EXISTS {TABLE} ("
    " seq bigserial PRIMARY KEY,"
    " at timestamptz NOT NULL DEFAULT now(),"
    " owner text NOT NULL, corpus_id text NOT NULL, doc_id text NOT NULL,"
    " sha256 text NOT NULL, bytes int NOT NULL, body text NOT NULL,"
    " deleted boolean NOT NULL DEFAULT false)",
    f"CREATE INDEX IF NOT EXISTS {TABLE}_doc ON {TABLE} (owner, corpus_id, doc_id, seq DESC)",
)
_NEWEST = (f"SELECT seq, at, sha256, bytes, deleted FROM {TABLE}"
           " WHERE owner=$1 AND corpus_id=$2 AND doc_id=$3 ORDER BY seq DESC LIMIT 1")
_ready = False
_lock = asyncio.Lock()


async def ensure() -> None:
    """The table, on its own connection before anything writes — `corpus_schema.ensure`'s reason."""
    global _ready
    if _ready or not db.dsn():
        return
    async with _lock:
        if not _ready:
            async with db.acquire() as conn:
                for statement in DDL:
                    await conn.execute(statement)
            _ready = True


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _meta(row: object) -> dict:
    return {"version": row["seq"], "at": row["at"].isoformat(), "sha256": row["sha256"],  # type: ignore[index]
            "bytes": row["bytes"], "deleted": row["deleted"]}  # type: ignore[index]


async def record(owner: str, corpus_id: str, doc_id: str, text: str) -> tuple[dict, bool]:
    """Append `text` as the document's newest version unless it already is. Returns
    (the newest version's metadata, whether this call appended it)."""
    await ensure()
    sha = digest(text)
    async with db.acquire(statement_timeout_ms=STATEMENT_TIMEOUT_MS) as conn:
        newest = await conn.fetchrow(_NEWEST, owner, corpus_id, doc_id)
        if newest is not None and newest["sha256"] == sha and not newest["deleted"]:
            return _meta(newest), False
        row = await conn.fetchrow(
            f"INSERT INTO {TABLE} (owner, corpus_id, doc_id, sha256, bytes, body)"
            " VALUES ($1,$2,$3,$4,$5,$6) RETURNING seq, at, sha256, bytes, deleted",
            owner, corpus_id, doc_id, sha, len(text.encode("utf-8")), text)
    return _meta(row), True


async def read(owner: str, corpus_id: str, doc_id: str, version: int | None = None) -> dict | None:
    """One version's exact text — the newest when `version` is None. A deleted
    document reads as None at its newest, but each older version stays readable."""
    await ensure()
    sql = (f"SELECT seq, at, sha256, bytes, deleted, body FROM {TABLE}"
           " WHERE owner=$1 AND corpus_id=$2 AND doc_id=$3")
    args: tuple = (owner, corpus_id, doc_id)
    sql, args = (sql + " AND seq=$4", (*args, version)) if version else (sql + " ORDER BY seq DESC LIMIT 1", args)
    async with db.acquire(statement_timeout_ms=STATEMENT_TIMEOUT_MS) as conn:
        row = await conn.fetchrow(sql, *args)
    if row is None or row["deleted"]:
        return None
    return {**_meta(row), "doc_id": doc_id, "text": row["body"]}


async def history(owner: str, corpus_id: str, doc_id: str) -> list[dict]:
    """Every version of one document, newest first, without the bodies."""
    await ensure()
    async with db.acquire(statement_timeout_ms=STATEMENT_TIMEOUT_MS) as conn:
        rows = await conn.fetch(
            f"SELECT seq, at, sha256, bytes, deleted FROM {TABLE}"
            " WHERE owner=$1 AND corpus_id=$2 AND doc_id=$3 ORDER BY seq DESC",
            owner, corpus_id, doc_id)
    return [_meta(r) for r in rows]


async def tombstone(owner: str, corpus_id: str, doc_id: str | None = None) -> int:
    """Mark one document — or every live one in the corpus — deleted, by appending.
    The versions before the tombstone stay: deleting is a new fact, not an erasure."""
    await ensure()
    async with db.acquire(statement_timeout_ms=STATEMENT_TIMEOUT_MS) as conn:
        tag = await conn.execute(
            f"INSERT INTO {TABLE} (owner, corpus_id, doc_id, sha256, bytes, body, deleted)"
            " SELECT owner, corpus_id, doc_id, '', 0, '', true FROM ("
            "  SELECT DISTINCT ON (doc_id) owner, corpus_id, doc_id, deleted"
            f"  FROM {TABLE} WHERE owner=$1 AND corpus_id=$2 AND ($3::text IS NULL OR doc_id=$3)"
            "  ORDER BY doc_id, seq DESC) newest WHERE NOT newest.deleted",
            owner, corpus_id, doc_id)
    return int(tag.rsplit(" ", 1)[-1] or 0)
