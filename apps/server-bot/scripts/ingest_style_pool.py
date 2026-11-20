"""Load a persona's voice pool: one curated line per row, replacing the namespace.

Usage:
    POSTGRES_URL=... python scripts/ingest_style_pool.py --persona insult [--dry-run]

Reads every `.txt` under `data/style/<persona_id>/` (gitignored; the folder's
MANIFEST.md says what is in it and why), one example per non-empty line, and
writes them to the persona's `style_namespace`. The pool is curated by hand, so
a load REPLACES the namespace instead of merging: a line removed from the file
must stop reaching the model.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from persona_core.corpus.pg_rag import connect, embed_passage  # noqa: E402
from shared.personas.registry import get_persona  # noqa: E402


def read_pool(persona_id: str) -> list[tuple[str, str]]:
    """(source_ref, line) for every non-empty line of every pool file."""
    out: list[tuple[str, str]] = []
    for path in sorted((ROOT / "data" / "style" / persona_id).glob("*.txt")):
        ref = f"{persona_id}-style:{path.stem}"
        out.extend((ref, line.strip()) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return out


async def main() -> int:
    parser = argparse.ArgumentParser(description="Load a persona voice pool into its style namespace.")
    parser.add_argument("--persona", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    persona = get_persona(args.persona)
    namespace = getattr(persona, "style_namespace", None) if persona else None
    if not namespace:
        print(f"FATAL: persona {args.persona!r} has no style_namespace in the registry", file=sys.stderr)
        return 1
    pool = read_pool(args.persona)
    if not pool:
        print(f"FATAL: no lines under data/style/{args.persona}/*.txt", file=sys.stderr)
        return 1
    print(f"persona={args.persona} namespace={namespace} lines={len(pool)}")
    if args.dry_run:
        return 0
    if not os.environ.get("POSTGRES_URL"):
        print("FATAL: POSTGRES_URL is not set", file=sys.stderr)
        return 1

    rows = []
    for ref, line in pool:
        vec = await embed_passage(line)
        if vec is None:
            print(f"FATAL: embedding failed for a line of {ref}", file=sys.stderr)
            return 1
        rows.append((namespace, "style", ref, line, vec))

    conn = await connect()
    if conn is None:
        print("FATAL: could not connect to Postgres", file=sys.stderr)
        return 1
    try:
        async with conn.transaction():
            deleted = await conn.execute("DELETE FROM deep_memory_chunks WHERE user_id = $1", namespace)
            await conn.executemany(
                """
                INSERT INTO deep_memory_chunks (user_id, source_type, source_ref, chunk_text, embedding)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id, source_ref, md5(chunk_text)) DO NOTHING
                """,
                rows,
            )
        count = await conn.fetchval("SELECT count(*) FROM deep_memory_chunks WHERE user_id = $1", namespace)
    finally:
        await conn.close()
    print(f"{deleted}; now {count} lines in {namespace}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
