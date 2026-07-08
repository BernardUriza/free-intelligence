"""Shared asyncpg + pgvector connection bootstrap.

One home for the well-known asyncpg pitfall both Postgres-backed stores
had privately fixed (``PgVectorChunkStore`` first, ``PgMemoryStore``
copy-pasting "same fix here"): the ``vector`` extension must exist
BEFORE the pool is built, because asyncpg's per-connection codec lookup
races against a not-yet-created type and fails with
``unknown type: public.vector``. The sequence is always:

1. ``ensure_vector_extension(dsn)`` — one-shot bare connection,
   ``CREATE EXTENSION IF NOT EXISTS vector``.
2. ``create_vector_pool(dsn, ...)`` — pool whose per-connection ``init``
   registers the pgvector codec so ``vector(N)`` columns round-trip as
   ``list[float]`` without explicit casts.

Codec registration is tolerant of a still-missing extension (skipped
silently) so a pool built from a DSN before schema-init stays usable;
the store's ``init_schema()`` is expected to install the extension and
let subsequent connections pick the codec up.

Optional dependency: ``asyncpg`` + ``pgvector``. Install via
``pip install 'fi-core[stores-pgvector]'``.
"""

from __future__ import annotations

try:
    import asyncpg
    from pgvector.asyncpg import register_vector
except ImportError as e:
    raise ImportError(
        "fi_core.stores._pg requires asyncpg and pgvector. "
        "Install via: pip install 'fi-core[stores-pgvector]'"
    ) from e


async def ensure_vector_extension(dsn: str) -> None:
    """Install the ``vector`` extension via a one-shot bare connection.

    Must run BEFORE the pool exists (see module docstring). Requires the
    connecting role to have ``CREATE`` privilege on the database, or the
    extension to be pre-installed by a superuser (typical in managed
    Postgres products).
    """
    bare = await asyncpg.connect(dsn)
    try:
        await bare.execute("CREATE EXTENSION IF NOT EXISTS vector")
    finally:
        await bare.close()


async def init_vector_connection(conn: "asyncpg.Connection") -> None:
    """Pool ``init=`` callback: register the pgvector codec.

    Tolerant of the case where the extension isn't installed yet — the
    codec is skipped silently and the caller is expected to run the
    store's ``init_schema()`` to install + reopen.
    """
    try:
        await register_vector(conn)
    except Exception:
        pass


async def create_vector_pool(
    dsn: str,
    *,
    min_size: int = 1,
    max_size: int = 4,
) -> "asyncpg.Pool":
    """Build a pool whose every connection carries the pgvector codec."""
    pool = await asyncpg.create_pool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        init=init_vector_connection,
    )
    assert pool is not None
    return pool
