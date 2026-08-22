"""Where the gateway's memory is KEPT: the schema, the pool, and the blob table.

Split out of `gateway_mirror` on 2026-08-22, when #41 added a second table and
the module was carrying three concepts at once. The cut is the one the rules
already name: **the daemon owns the DDL** ([[write-only-daemon]] §3), and a
schema change is an API change between the two halves — so the contract the
front reads deserves a home of its own, the way `deps.py` is the engine's.

`gateway_mirror` now answers only "what gets appended"; this module answers
"where, and under what shape".
"""

from __future__ import annotations

import json
import os
from typing import Any

_pool: Any = None
# Fingerprints this process has already written (#41). A cache, never memory: a
# restart just re-attempts an INSERT that does nothing.
_stored: set[str] = set()

DDL = """
CREATE TABLE IF NOT EXISTS aire_gateway_log (
  seq             bigserial PRIMARY KEY,
  ts              timestamptz NOT NULL DEFAULT now(),
  exchange        text NOT NULL,
  kind            text NOT NULL,
  session_id      text,
  agent_id        text,
  parent_agent_id text,
  project         text,
  model           text,
  body            jsonb,
  stop_reason     text,
  usage           jsonb,
  status          int,
  holder          text
);
CREATE INDEX IF NOT EXISTS aire_gateway_log_session_idx
  ON aire_gateway_log (session_id);
CREATE INDEX IF NOT EXISTS aire_gateway_log_exchange_idx
  ON aire_gateway_log (exchange);
ALTER TABLE aire_gateway_log ADD COLUMN IF NOT EXISTS holder text;

-- #41: the handful of values every request repeats (33 distinct system arrays
-- and 9 tool sets across 585 measured rows), each kept once under its
-- fingerprint. Created as role `aire`, so the reader's default-privileges grant
-- covers it the moment it exists.
CREATE TABLE IF NOT EXISTS aire_gateway_blob (
  fingerprint text PRIMARY KEY,
  first_seen  timestamptz NOT NULL DEFAULT now(),
  body        jsonb NOT NULL
);
"""


def dsn() -> str:
    return os.environ.get("AIRE_DSN", "postgresql://bernardurizaorozco@127.0.0.1:5432/aire")


async def pool() -> Any:
    global _pool
    if _pool is None:
        import asyncpg
        _pool = await asyncpg.create_pool(dsn(), min_size=0, max_size=2)
        await _pool.execute(DDL)
    return _pool


async def reset() -> None:
    """Drop the cached pool and the fingerprint cache — a database that went
    away and came back, or a test that wants a cold process."""
    global _pool
    _stored.clear()
    if _pool is not None:
        await _pool.close()
        _pool = None


async def store_blobs(blobs: dict[str, Any]) -> bool:
    """Keep each repeated value once. False means the caller must inline them
    instead: a reference to a row that was never written is a dangling pointer,
    and the front that reads this log cannot repair one."""
    fresh = {f: v for f, v in blobs.items() if f not in _stored}
    if not fresh:
        return True
    try:
        conn = await pool()
        for digest, value in fresh.items():
            await conn.execute(
                "INSERT INTO aire_gateway_blob (fingerprint, body) VALUES ($1, $2::jsonb)"
                " ON CONFLICT (fingerprint) DO NOTHING", digest, json.dumps(value))
            _stored.add(digest)
        return True
    except Exception as exc:  # noqa: BLE001 — degrade to a fat row, never a dangling ref
        print(f"GATEWAY-MIRROR blob append failed: {type(exc).__name__}: {exc}")
        return False
