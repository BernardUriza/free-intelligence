"""One-shot backfill: populate ``principal_facts.embedding`` (inline 384d).

The fi-core migration (v4.1.0) moved fact embeddings from the standalone
``fact_embeddings`` table to the inline ``principal_facts.embedding`` column
that ``fi_core.memory.PgMemoryStore`` reads in ``semantic_search``. Existing
rows predate that column being written, so at cutover their inline
``embedding`` is NULL and semantic search would silently degrade to unranked
``get_facts`` for them until the next ``save_facts`` re-embeds.

We re-embed from scratch (NOT a copy from ``fact_embeddings``) on purpose:
the legacy ``fact_embeddings`` table only ever held ``source='auto'`` rows —
``add_manual_fact`` / ``add_remember_fact`` / consolidation merges never
wrote to it — so a copy would leave manual + agent + merged facts unsearchable.
Re-embedding every live row with the same MiniLM model covers all tiers.

Idempotent: only touches rows where ``embedding IS NULL``. Safe to re-run.

Usage (POSTGRES_URL in env; run from an env that has fi-core + the model)::

    python -m scripts.backfill_facts_inline_embeddings           # all users
    python -m scripts.backfill_facts_inline_embeddings --user 907264175246569543
    python -m scripts.backfill_facts_inline_embeddings --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg
import structlog

log = structlog.get_logger()


async def _connect() -> asyncpg.Connection:
    url = os.environ.get("POSTGRES_URL")
    if not url:
        print("POSTGRES_URL not set", file=sys.stderr)
        raise SystemExit(2)
    conn = await asyncpg.connect(url)
    from pgvector.asyncpg import register_vector

    await register_vector(conn)
    return conn


async def backfill(*, user_id: str | None, dry_run: bool) -> int:
    from pgvector import Vector

    from insult.core.vectors import get_embedding_model

    model = get_embedding_model()
    conn = await _connect()
    try:
        if user_id:
            rows = await conn.fetch(
                "SELECT id, fact FROM principal_facts "
                "WHERE deleted_at IS NULL AND embedding IS NULL AND principal_id = $1 "
                "ORDER BY id",
                user_id,
            )
        else:
            rows = await conn.fetch(
                "SELECT id, fact FROM principal_facts WHERE deleted_at IS NULL AND embedding IS NULL ORDER BY id",
            )
        print(f"rows to backfill: {len(rows)}{' (dry-run)' if dry_run else ''}")
        if dry_run or not rows:
            return len(rows)

        done = 0
        for r in rows:
            try:
                vec = Vector(model.embed(r["fact"]))
            except Exception as e:  # skip a bad row, keep going
                log.warning("backfill_embed_failed", fact_id=r["id"], error=str(e))
                continue
            await conn.execute(
                "UPDATE principal_facts SET embedding = $1 WHERE id = $2",
                vec,
                r["id"],
            )
            done += 1
            if done % 25 == 0:
                print(f"  ...{done}/{len(rows)}")
        print(f"backfilled {done}/{len(rows)} rows")
        return done
    finally:
        await conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill inline fact embeddings")
    ap.add_argument("--user", default=None, help="principal_id to limit to (default: all)")
    ap.add_argument("--dry-run", action="store_true", help="count only, no writes")
    args = ap.parse_args()
    asyncio.run(backfill(user_id=args.user, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
