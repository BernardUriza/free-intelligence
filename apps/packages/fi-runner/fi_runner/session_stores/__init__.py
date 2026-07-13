"""SessionStore adapters — the durable memory of a Claude Agent SDK session.

Lazy by construction. A store pulls in the SDK (and, for Postgres, a database
driver), and fi-runner must import neither just because something imported
fi-runner. Nothing here is loaded until it is named:

    from fi_runner.session_stores import PostgresSessionStore   # imports now, not before
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "PostgresSessionStore",
    "PostgresSessionStoreOptions",
    "create_postgres_session_store",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from . import postgres

        return getattr(postgres, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
