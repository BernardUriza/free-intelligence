"""The shared engine singleton, built lazily against Postgres. Its own module so
every router (messages, artifacts) can reach it WITHOUT importing server.py —
that would be circular. The pool dies with the database; a dropped engine just
rebuilds on the next call (the store is the truth, the pool a cache)."""

from __future__ import annotations

import os

from .engine import Engine
from .store import create_postgres_session_store

DSN = os.environ.get("AIRE_DSN", "postgresql://bernardurizaorozco@127.0.0.1:5432/aire")

_engine: Engine | None = None


async def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = Engine(await create_postgres_session_store(DSN))
    return _engine


def drop_engine() -> None:
    """The cached pool (store + clients) dies with the database; let the next
    request rebuild it against the database once it's back up."""
    global _engine
    _engine = None
