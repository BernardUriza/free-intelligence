"""Fill `deep_memory_chunks.embedding` (384d, multilingual e5) from `chunk_text`.

The 2026-11-20 migration in `persona_core/memory/postgres_schema.sql` moved the
ada-002 vectors to `embedding_ada002` and left the new column NULL. This script
re-embeds the rows a live reader can reach, in batches, and is resumable: it
only ever touches rows whose `embedding IS NULL`.

Skipped by default: `__chatgpt_archive__`. Nothing reads it (the `deep_memory`
tool searches the caller's own snowflake and the auto-recall that used it was
removed on 2026-06-03), and it is 30k of the 37k rows. Pass `--include-archive`
the day something needs it.

CLI:
    conda activate discord-bot
    export POSTGRES_URL=$(cat ~/.secrets/discord-bot-postgres-url.txt)
    python scripts/reembed_deep_memory.py --apply-schema   # migrate, then fill
    python scripts/reembed_deep_memory.py --dry-run        # count only
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

import asyncpg

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

_ARCHIVE = "__chatgpt_archive__"
_SCHEMA = _REPO_ROOT / "persona_core" / "memory" / "postgres_schema.sql"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apply-schema", action="store_true", help="run postgres_schema.sql first (idempotent)")
    p.add_argument("--include-archive", action="store_true", help=f"also re-embed {_ARCHIVE}")
    p.add_argument("--dry-run", action="store_true", help="count pending rows and exit")
    p.add_argument("--batch", type=int, default=64)
    return p.parse_args()


def _scope_sql(include_archive: bool) -> tuple[str, list]:
    if include_archive:
        return "embedding IS NULL", []
    return "embedding IS NULL AND user_id <> $1", [_ARCHIVE]


async def main() -> int:
    args = parse_args()
    url = os.environ.get("POSTGRES_URL")
    if not url:
        print("FATAL: POSTGRES_URL not set", file=sys.stderr)
        return 2

    from pgvector.asyncpg import register_vector

    conn = await asyncpg.connect(url, timeout=20)
    try:
        if args.apply_schema:
            await conn.execute(_SCHEMA.read_text(encoding="utf-8"))
            print("schema applied")
        await register_vector(conn)
        where, params = _scope_sql(args.include_archive)
        pending = await conn.fetchval(f"SELECT count(*) FROM deep_memory_chunks WHERE {where}", *params)  # nosec B608
        print(f"pending rows: {pending}")
        if args.dry_run or not pending:
            return 0

        from persona_core.corpus.pg_rag import encode

        done = 0
        started = time.monotonic()
        while True:
            rows = await conn.fetch(
                f"SELECT id, chunk_text FROM deep_memory_chunks WHERE {where} ORDER BY id LIMIT {int(args.batch)}",  # nosec B608
                *params,
            )
            if not rows:
                break
            vecs = await asyncio.gather(*(encode(r["chunk_text"], role="passage") for r in rows))
            await conn.executemany(
                "UPDATE deep_memory_chunks SET embedding = $2 WHERE id = $1",
                [(r["id"], v) for r, v in zip(rows, vecs, strict=True)],
            )
            done += len(rows)
            rate = done / max(time.monotonic() - started, 1e-6)
            print(f"  {done}/{pending} ({rate:.1f}/s)", flush=True)

        left = await conn.fetchval(f"SELECT count(*) FROM deep_memory_chunks WHERE {where}", *params)  # nosec B608
        print(f"done: {done} re-embedded, {left} still NULL in scope")
        return 0 if left == 0 else 1
    finally:
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
