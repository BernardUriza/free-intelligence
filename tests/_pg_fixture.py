"""asyncpg-pool fixture backed by a per-session ephemeral Postgres.

Reactivates the SQLite-era DB-touching tests against the new asyncpg
data plane WITHOUT requiring docker or a long-running Postgres service.
`pytest-postgresql` spins up a postgres binary into a tempdir, applies
the schema, hands us the connection info; we wrap that in an
`asyncpg.Pool` and build a real `MemoryStore`.

How CI sees this:
- If `pg_ctl` for the right version is present + pgvector is installed,
  these tests run.
- If not, every fixture that depends on `pg_memory_store` is auto-skipped
  via `pytestmark = REQUIRES_PG`. Same mechanism we used for the SQLite
  retirement: tests stay green by default, the developer with PG locally
  gets the deeper coverage.

Why a separate module rather than dumping into `conftest.py`:
- `pytest-postgresql`'s `factories.postgresql_proc` is constructed at
  import time and probes the binary path. Hiding it behind a guarded
  import keeps `tests/conftest.py` working on machines without
  postgres@17 — running the regular suite there shouldn't choke.
- Importing this module from `conftest.py` only when the binary exists
  lets us keep the import-time side effect contained.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# --- Postgres binary discovery -----------------------------------------------
#
# Mac dev box: `brew install postgresql@17` lands here. Linux CI typically uses
# `/usr/lib/postgresql/17/bin/pg_ctl` (the canonical Debian/Ubuntu layout).
# Override with `INSULT_PG_CTL` env var if neither default applies. Detection
# is at import time so the skip marker reflects reality before the test runs.

_PG_CTL_CANDIDATES = [
    os.environ.get("INSULT_PG_CTL"),
    "/opt/homebrew/opt/postgresql@17/bin/pg_ctl",  # mac arm64 brew
    "/usr/local/opt/postgresql@17/bin/pg_ctl",  # mac intel brew
    "/usr/lib/postgresql/17/bin/pg_ctl",  # Debian/Ubuntu apt
]


def _find_pg_ctl() -> str | None:
    for cand in _PG_CTL_CANDIDATES:
        if cand and Path(cand).exists():
            return cand
    return None


PG_CTL = _find_pg_ctl()

REQUIRES_PG = pytest.mark.skipif(
    PG_CTL is None,
    reason=(
        "no pg_ctl found in standard locations (set INSULT_PG_CTL env var to "
        "point at one — e.g. /opt/homebrew/opt/postgresql@17/bin/pg_ctl)"
    ),
)

# --- pytest-postgresql wiring -----------------------------------------------
#
# These factories are imported into conftest.py via star-import below. The
# `postgresql_proc` factory creates a per-session daemon; `postgresql_socket`
# (renamed from the default `postgresql` so we don't shadow the model) yields
# a psycopg connection PER TEST that the fixture itself uses to apply the
# schema before each asyncpg test starts.

if PG_CTL is not None:
    from pytest_postgresql import factories

    _SCHEMA = Path(__file__).resolve().parent.parent / "khimeras_shared" / "memory" / "postgres_schema.sql"

    # `load` accepts `Path` instances (treated as SQL files) OR `"pkg.mod:fn"`
    # callable specs. Passing `str(_SCHEMA)` makes pytest-postgresql think
    # it's a module path; pass the `Path` object so the loader runs it as a
    # SQL file. The schema's `CREATE EXTENSION IF NOT EXISTS vector` line
    # works inside the target DB.
    postgresql_proc = factories.postgresql_proc(
        executable=PG_CTL,
        port=None,  # let pytest-postgresql pick a free port
        load=[_SCHEMA],
    )
    postgresql_socket = factories.postgresql("postgresql_proc")

# --- Fixture exposed to tests ------------------------------------------------


@pytest.fixture
async def pg_memory_store(postgresql_socket):
    """Real MemoryStore wired to an ephemeral PG17 with the live schema applied.

    Each test gets a fresh database; no cross-test pollution. Schema is the
    canonical `postgres_schema.sql` so we exercise the same DDL that prod
    sees — placeholder errors, index names, type coercions all matter here.
    """
    from khimeras_shared.memory import MemoryStore

    info = postgresql_socket.info
    # asyncpg DSN format: `postgresql://user@host:port/dbname`. pytest-postgresql
    # binds to localhost; password is empty for the dev-user it creates.
    dsn = (
        f"postgresql://{info.user}:{info.password}@{info.host}:{info.port}/{info.dbname}"
        if info.password
        else f"postgresql://{info.user}@{info.host}:{info.port}/{info.dbname}"
    )
    store = MemoryStore(dsn)
    await store.connect()
    try:
        yield store
    finally:
        await store.close()
