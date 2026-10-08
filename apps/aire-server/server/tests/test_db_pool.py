"""One pool per process, and a bound that does not follow the connection home.

Five modules opened their own connection per call. Measured from the droplet
against the real database: **185–236 ms to connect, 12–29 ms to run the query**
— fifteen times longer opening the door than walking through it, paid by
`tokens.charge` on every billed gateway turn and by `memory_tool` inside a paid
turn. A warm `acquire()` on the same box costs 0.0–0.6 ms.

Two things can regress here and neither is loud: a new call site quietly going
back to `asyncpg.connect`, and a per-query bound set on a POOLED connection,
which would then govern whoever borrows it next.
"""

import asyncio
import re
from pathlib import Path

import pytest

from aire import db

AIRE = Path(__file__).resolve().parent.parent / "aire"
# Not every direct connect is the defect. These open ONE connection for a whole
# process run or a whole daemon lifetime, which is already the right lifetime:
#   store.py     — the SDK's upstream example, kept diffable on purpose
#   listen/pen.py — the pen's long-lived reconnecting connection
#   mirror.py / restore.py — a oneshot's single connection for its single run
LONG_LIVED = {"store.py", "listen/pen.py", "mirror.py", "restore.py"}
DIRECT = re.compile(r"asyncpg\.connect\(")


def test_no_call_site_opens_its_own_connection_again():
    offenders = [f"{p.relative_to(AIRE)}:{i}"
                 for p in AIRE.rglob("*.py")
                 if str(p.relative_to(AIRE)) not in LONG_LIVED
                 for i, line in enumerate(p.read_text().splitlines(), 1)
                 if DIRECT.search(line) and not line.lstrip().startswith("#")]
    assert offenders == [], offenders


@pytest.mark.asyncio
async def test_the_pool_is_built_once_and_reused():
    await db.close()
    first = await db.pool()
    assert await db.pool() is first, "a second call rebuilt the pool"
    async with db.acquire() as conn:
        assert await conn.fetchval("SELECT 1") == 1
    await db.close()


@pytest.mark.asyncio
async def test_a_query_bound_does_not_follow_the_connection_back_to_the_pool():
    """The hazard a pool introduces that a fresh connection never had. The old
    `memory_tool` set `statement_timeout` as a connection-level server_setting;
    on a pooled connection that would outlive the query and silently cap the
    next borrower — a scan aborting for a reason nobody could see."""
    await db.close()
    async with db.acquire(statement_timeout_ms=5_000) as conn:
        assert await conn.fetchval("SHOW statement_timeout") == "5s"
    async with db.acquire() as conn:
        assert await conn.fetchval("SHOW statement_timeout") != "5s", \
            "the bound rode the connection back into the pool"
    await db.close()


def test_a_second_event_loop_gets_its_own_pool():
    """A pool belongs to the loop that created it. A oneshot re-entered, or a
    test suite that builds a loop per test, would otherwise await connections
    from a loop that no longer runs."""
    async def grab():
        return await db.pool()

    first = asyncio.run(grab())
    second = asyncio.run(grab())
    assert first is not second, "a pool from a dead loop was handed out again"
    # And tidying up from a THIRD loop must not raise: closing a pool whose loop
    # is gone is the caller doing the right thing, not an error.
    asyncio.run(db.close())
    assert db._pool is None
