"""The corpus table's SHAPE, and how a live one reaches the current version.

Split from `corpus.py` because they change for different reasons and at different
times: the store reads and writes rows every turn, while this runs once at startup
and then never again. Migrations also only ever accumulate, and the store should
not grow a line every time the schema learns something.
"""

from __future__ import annotations

import asyncio

from . import db

TABLE = "aire_corpus_chunk"
DDL = (
    f"CREATE TABLE IF NOT EXISTS {TABLE} ("
    " seq bigserial PRIMARY KEY,"
    " at timestamptz NOT NULL DEFAULT now(),"
    " owner text NOT NULL,"
    " corpus_id text NOT NULL,"
    " doc_id text NOT NULL,"
    " ord int NOT NULL,"
    " body text NOT NULL,"
    " norm text NOT NULL DEFAULT '',"
    " fts tsvector GENERATED ALWAYS AS (to_tsvector('spanish', norm)) STORED)"
)
# The shape shipped hours before `norm` existed, indexing accented text directly —
# so `telemetría` did not match `telemetria` (see `chunking.fold`). These bring an
# existing table to the current shape and are no-ops afterwards. The generated
# column is DROPPED and rebuilt rather than altered because a generated column's
# expression cannot be changed in place; nothing is lost, since Postgres recomputes
# it from `norm` the moment it is added.
MIGRATIONS = (
    f"ALTER TABLE {TABLE} ADD COLUMN IF NOT EXISTS norm text NOT NULL DEFAULT ''",
    f"UPDATE {TABLE} SET norm = body WHERE norm = ''",
    f"ALTER TABLE {TABLE} DROP COLUMN IF EXISTS fts",
    f"ALTER TABLE {TABLE} ADD COLUMN fts tsvector"
    " GENERATED ALWAYS AS (to_tsvector('spanish', norm)) STORED",
)
INDEXES = (
    f"CREATE INDEX IF NOT EXISTS aire_corpus_fts ON {TABLE} USING GIN (fts)",
    f"CREATE INDEX IF NOT EXISTS aire_corpus_doc ON {TABLE} (owner, corpus_id, doc_id)",
)

_ready = False
_lock = asyncio.Lock()


async def ensure() -> None:
    """The table, committed and visible to other connections, before anything
    writes — on its OWN connection outside any transaction, for the reason
    `spend.ensure` documents in full: a flag flipped over an uncommitted CREATE
    sends every other coroutine at a table it cannot see."""
    global _ready
    if _ready or not db.dsn():
        return
    async with _lock:
        if _ready:
            return
        async with db.acquire() as conn:
            await conn.execute(DDL)
            if not await _folded(conn):
                for statement in MIGRATIONS:
                    await conn.execute(statement)
            for index in INDEXES:
                await conn.execute(index)
        _ready = True


async def _folded(conn: object) -> bool:
    """Is the table already indexing the folded copy? Asked of the catalog rather
    than assumed, so the migration runs exactly once and the rebuild of a
    generated column never happens on a healthy startup."""
    return bool(await conn.fetchval(  # type: ignore[attr-defined]
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name=$1 AND column_name='norm'", TABLE))
