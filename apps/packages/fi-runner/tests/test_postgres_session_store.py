"""The Postgres SessionStore must satisfy the SDK's OWN conformance suite.

The green criterion is not one we invented: `claude_agent_sdk.testing` ships
`run_session_store_conformance`, 14 contracts the SDK exercises against any
adapter. Passing our own hand-written assertions would prove nothing about what
the SDK actually expects at runtime.

The database is EPHEMERAL and OFFLINE: a Postgres cluster is initdb'd into a
tmpdir, run on a unix socket, and torn down. Nothing is installed, nothing is
reached over the network, nothing persists.

Skipped (never failed red) when asyncpg or the Postgres binaries are absent —
the store lives behind the optional `[postgres]` extra, and a machine without it
is not a broken machine.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator

import pytest

asyncpg = pytest.importorskip("asyncpg", reason="the [postgres] extra is not installed")
pytest.importorskip("claude_agent_sdk", reason="the [claude] extra is not installed")

from claude_agent_sdk.testing import run_session_store_conformance  # noqa: E402

from fi_runner.session_stores import PostgresSessionStore  # noqa: E402

def _pg_bin(name: str) -> str | None:
    """The SERVER's binary, not the client's. `which initdb` can land on libpq's
    bin dir (client-only), whose initdb is not the server's — mixing them fails at
    initdb time. Prefer an explicit server install, then fall back to PATH.
    """
    for prefix in ("/opt/homebrew/opt/postgresql@17/bin", "/usr/local/opt/postgresql@17/bin"):
        candidate = os.path.join(prefix, name)
        if os.path.exists(candidate):
            return candidate
    return shutil.which(name)


_INITDB, _PG_CTL = _pg_bin("initdb"), _pg_bin("pg_ctl")
pytestmark = pytest.mark.skipif(
    not (_INITDB and _PG_CTL),
    reason="no local Postgres server binaries (initdb/pg_ctl) to run an ephemeral cluster",
)


@pytest.fixture(scope="module")
def ephemeral_postgres() -> Iterator[str]:
    """An throwaway Postgres on a unix socket in a tmpdir. Offline; no network."""
    tmp = tempfile.mkdtemp(prefix="fi-runner-pg-")
    data = os.path.join(tmp, "data")
    subprocess.run(
        [_INITDB, "-D", data, "-U", "postgres", "--auth=trust", "-E", "UTF8"],
        check=True,
        capture_output=True,
    )
    # Listen ONLY on a unix socket in the tmpdir: no TCP port to collide with a
    # developer's own Postgres (this repo has been bitten by a :5432 squatter).
    #
    # `-l` (a log FILE) is not cosmetic: pg_ctl daemonizes the server, which
    # INHERITS whatever stdout/stderr it was given. With capture_output=True the
    # daemon holds the pipe open forever, so subprocess.run blocks waiting for an
    # EOF that never comes — the run hangs after "collected 2 items" while the
    # same commands work by hand. Give the server a file and it detaches cleanly.
    subprocess.run(
        [
            _PG_CTL, "-D", data, "-l", os.path.join(tmp, "server.log"), "-o",
            f"-k {tmp} -c listen_addresses='' -c fsync=off -c full_page_writes=off",
            "-w", "start",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        yield f"postgresql://postgres@/postgres?host={tmp}"
    finally:
        subprocess.run(
            [_PG_CTL, "-D", data, "-m", "immediate", "-w", "stop"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        shutil.rmtree(tmp, ignore_errors=True)


def test_conformance_suite(ephemeral_postgres: str) -> None:
    """All 14 SDK contracts, against the real adapter on a real Postgres."""
    counter = {"n": 0}

    async def make_store() -> PostgresSessionStore:
        # A fresh table per store: the suite builds several and they must not see
        # each other's rows.
        counter["n"] += 1
        pool = await asyncpg.create_pool(ephemeral_postgres, min_size=1, max_size=4)
        store = PostgresSessionStore(pool=pool, table=f"conformance_{counter['n']}")
        await store.create_schema()
        return store

    # It is a COROUTINE (verified: inspect.iscoroutinefunction is True). Calling it
    # without awaiting would assert nothing and pass — a green that proves nothing.
    asyncio.run(run_session_store_conformance(make_store))


def test_append_deduplicates_by_uuid(ephemeral_postgres: str) -> None:
    """The adaptation upstream does not have: a re-sent entry lands ONCE.

    The SDK may re-send an entry it already flushed (a retry, a reconnect). The
    upstream adapter inserts it again — `seq` is a bigserial and nothing stops it
    — so a resumed transcript would replay the same tool_result twice. That is a
    corrupted memory, not a cosmetic wart.
    """

    async def go() -> None:
        pool = await asyncpg.create_pool(ephemeral_postgres, min_size=1, max_size=2)
        store = PostgresSessionStore(pool=pool, table="dedupe_check")
        await store.create_schema()
        key = {"project_key": "p", "session_id": "s"}

        entry = {"uuid": "u-1", "type": "user", "message": {"role": "user", "content": "hola"}}
        await store.append(key, [entry])
        await store.append(key, [entry])  # the SDK re-sends it
        await store.append(key, [entry, {"uuid": "u-2", "type": "assistant"}])

        loaded = await store.load(key)
        assert [e["uuid"] for e in loaded] == ["u-1", "u-2"], loaded

        # An entry with NO uuid is not deduplicated — it appends, as upstream does.
        await store.append(key, [{"type": "system"}])
        await store.append(key, [{"type": "system"}])
        assert len(await store.load(key)) == 4
        await pool.close()

    asyncio.run(go())
