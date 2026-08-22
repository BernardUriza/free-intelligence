"""The shared engine singleton, built lazily against Postgres. Its own module so
every router (messages, artifacts) can reach it WITHOUT importing server.py —
that would be circular. The pool dies with the database; a dropped engine just
rebuilds on the next call (the store is the truth, the pool a cache)."""

from __future__ import annotations

import os

from .engine import Engine
from .store import create_postgres_session_store


class MissingDSN(RuntimeError):
    """`AIRE_DATABASE_URL` is not set. Raised instead of defaulting, because the
    default this replaced was a developer's laptop — on the droplet that resolves
    to nothing, and the mirror swallows a dead connection by design, so the daemon
    would relay perfectly while its memory quietly stopped existing."""


def dsn() -> str:
    url = os.environ.get("AIRE_DATABASE_URL", "")
    if not url:
        raise MissingDSN("AIRE_DATABASE_URL is not set")
    return url


_engine: Engine | None = None


async def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = Engine(await create_postgres_session_store(dsn()))
    return _engine


def drop_engine() -> None:
    """The cached pool (store + clients) dies with the database; let the next
    request rebuild it against the database once it's back up."""
    global _engine
    _engine = None
