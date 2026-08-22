"""The broom may reclaim a deduped value, and may NEVER orphan a row (#41).

`aire_gateway_blob` holds each repeated `system`/`tools` once and the request
rows point at it by fingerprint. That makes the sweep the only place in this repo
where a DELETE can corrupt something else: remove a fingerprint a surviving row
still references and the front renders a `$ref` where a system prompt used to be,
with nothing able to repair it. So the referential half is tested as the load-
bearing claim it is — against a real Postgres, not a mock.
"""

import os
from contextlib import asynccontextmanager

import asyncpg
import pytest

from aire import sweep

DSN = os.environ.get("AIRE_DATABASE_URL", "postgresql://bernardurizaorozco@127.0.0.1:5432/aire")
LIVE = "live-fingerprint-0001"
ORPHAN = "orphan-fingerprint-0002"
YOUNG = "young-orphan-0003"


@asynccontextmanager
async def seeded():
    """A live Postgres with one referenced blob, one old orphan and one young
    one. The repo's tests use sync fixtures + @pytest.mark.asyncio, so the setup
    rides in a context manager rather than an async fixture."""
    c = await asyncpg.connect(DSN, timeout=10)
    await c.execute("""
        CREATE TABLE IF NOT EXISTS aire_gateway_log (
          seq bigserial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(),
          exchange text, kind text, body jsonb);
        CREATE TABLE IF NOT EXISTS aire_gateway_blob (
          fingerprint text PRIMARY KEY,
          first_seen timestamptz NOT NULL DEFAULT now(), body jsonb NOT NULL);
    """)
    await c.execute("DELETE FROM aire_gateway_blob WHERE fingerprint = ANY($1::text[])",
                    [LIVE, ORPHAN, YOUNG])
    await c.execute("DELETE FROM aire_gateway_log WHERE exchange LIKE 'sweeptest-%'")
    await _seed(c)
    try:
        yield c
    finally:
        await _cleanup(c)


async def _cleanup(c):
    await c.execute("DELETE FROM aire_gateway_blob WHERE fingerprint = ANY($1::text[])",
                    [LIVE, ORPHAN, YOUNG])
    await c.execute("DELETE FROM aire_gateway_log WHERE exchange LIKE 'sweeptest-%'")
    await c.close()


async def _seed(c):
    for fp, age_days in ((LIVE, 90), (ORPHAN, 90), (YOUNG, 0)):
        await c.execute(
            "INSERT INTO aire_gateway_blob (fingerprint, first_seen, body)"
            " VALUES ($1, now() - ($2::int * interval '1 day'), '[]'::jsonb)", fp, age_days)
    # One surviving row that still points at LIVE — and nothing points at the others.
    await c.execute(
        "INSERT INTO aire_gateway_log (exchange, kind, body) VALUES"
        " ('sweeptest-a', 'request', $1::jsonb)",
        '{"messages": [], "$elided": {"messages": 4, "system": {"$ref": "%s"}}}' % LIVE)
    # A row with no $elided at all must not break the scan.
    await c.execute(
        "INSERT INTO aire_gateway_log (exchange, kind, body) VALUES"
        " ('sweeptest-b', 'response', '{\"content\": []}'::jsonb)")


async def _present(c) -> set[str]:
    rows = await c.fetch("SELECT fingerprint FROM aire_gateway_blob WHERE fingerprint = ANY($1::text[])",
                         [LIVE, ORPHAN, YOUNG])
    return {r[0] for r in rows}


@pytest.mark.asyncio
async def test_a_referenced_fingerprint_survives_and_an_orphan_does_not():
    async with seeded() as conn:
        deleted = await sweep._sweep_blobs(conn, 30)
        left = await _present(conn)
        assert LIVE in left, "deleting a referenced blob orphans a row the front cannot repair"
        assert ORPHAN not in left, "an old blob nothing references is reclaimable space"
        assert deleted >= 1


@pytest.mark.asyncio
async def test_a_young_orphan_waits_out_the_daemons_cache():
    """The daemon caches which fingerprints it has already written, so a blob
    younger than the window may still be about to be referenced."""
    async with seeded() as conn:
        await sweep._sweep_blobs(conn, 30)
        assert YOUNG in await _present(conn)


@pytest.mark.asyncio
async def test_the_sweep_is_idempotent():
    async with seeded() as conn:
        await sweep._sweep_blobs(conn, 30)
        assert await sweep._sweep_blobs(conn, 30) == 0
        assert LIVE in await _present(conn)
