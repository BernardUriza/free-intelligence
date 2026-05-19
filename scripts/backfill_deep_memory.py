"""DM-3 backfill — ingest user message history into deep_memory_chunks.

Strategy: auto-discover users with enough recent activity to be worth
chunking (default: any user with >= MIN_MSGS_FOR_BACKFILL messages in
the lookback window). For each, pull messages chronologically, format
as `[YYYY-MM-DD HH:MM] speaker: content`, concatenate, hand to
fi_core's PARAGRAPH_AWARE chunker, embed with Azure OpenAI ada-002,
INSERT into deep_memory_chunks. Idempotent via the schema's unique
index on (user_id, source_ref, md5(chunk_text)).

source_ref format: `messages:<first_ts>-<last_ts>` (epoch seconds) so
the agent can cite "from late April 2026" when recalling a chunk.

CLI:
    # default: auto-discover all users with >=20 msgs in last 180d
    .venv/bin/python scripts/backfill_deep_memory.py

    # restrict to specific user_ids
    .venv/bin/python scripts/backfill_deep_memory.py --user-ids 907... 1431...

    # shorter lookback
    .venv/bin/python scripts/backfill_deep_memory.py --days 30 --min-msgs 5

    # dry-run (no inserts, just print what would happen)
    .venv/bin/python scripts/backfill_deep_memory.py --dry-run

Env required:
    POSTGRES_URL                       — PG connection string
    AZURE_OPENAI_ENDPOINT              — Azure cognitive endpoint
    AZURE_OPENAI_KEY                   — key for the account
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT  — defaults to text-embedding-ada-002

Run helper from this Mac (env injected from Azure secrets):
    PGURL=$(az containerapp secret show -n discord-bot -g insult-rg \\
        --secret-name postgres-url --query value -o tsv) \\
    AZURE_OPENAI_ENDPOINT=https://northcentralus.api.cognitive.microsoft.com/ \\
    AZURE_OPENAI_KEY=$(az cognitiveservices account keys list \\
        -n insult-openai -g insult-rg --query key1 -o tsv) \\
    POSTGRES_URL="$PGURL" ./.venv/bin/python scripts/backfill_deep_memory.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Run from the repo root regardless of where the script is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse

import asyncpg


def _fmt_ts(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=UTC).strftime("%Y-%m-%d %H:%M")


async def discover_active_users(
    conn: asyncpg.Connection, days: int, min_msgs: int
) -> list[tuple[str, str, int]]:
    """Find users with >= min_msgs messages in the last `days`.

    Returns [(user_id, last_seen_user_name, count), ...] sorted by
    count desc. Skips bot accounts (role='assistant') so we backfill
    only what the bot is recalling about humans.
    """
    cutoff = time.time() - days * 86400
    rows = await conn.fetch(
        """
        SELECT user_id,
               (ARRAY_AGG(user_name ORDER BY timestamp DESC))[1] AS last_name,
               COUNT(*) AS n
        FROM messages
        WHERE timestamp >= $1
          AND role = 'user'
        GROUP BY user_id
        HAVING COUNT(*) >= $2
        ORDER BY n DESC
        """,
        cutoff,
        min_msgs,
    )
    return [(r["user_id"], r["last_name"] or "?", r["n"]) for r in rows]


async def fetch_user_messages(conn: asyncpg.Connection, user_id: str, days: int) -> list[dict]:
    """All `role='user'` messages from this user_id in the last `days`, oldest first.

    Excludes assistant rows because chunking the bot's own replies into
    user-keyed memory would muddy what `deep_memory` recalls about the
    human. The bot's replies live in messages too (role='assistant',
    user_id=bot_id) and aren't tied to the human's namespace.
    """
    cutoff = time.time() - days * 86400
    rows = await conn.fetch(
        """
        SELECT id, channel_id, user_name, content, timestamp
        FROM messages
        WHERE user_id = $1
          AND timestamp >= $2
          AND role = 'user'
        ORDER BY timestamp ASC
        """,
        user_id,
        cutoff,
    )
    return [dict(r) for r in rows]


def format_message_block(msg: dict) -> str:
    return f"[{_fmt_ts(msg['timestamp'])}] {msg['user_name']}: {msg['content']}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else "")
    p.add_argument(
        "--user-ids",
        nargs="*",
        default=None,
        help="Restrict to these user_ids. Omit to auto-discover.",
    )
    p.add_argument("--days", type=int, default=180, help="Lookback window in days (default 180).")
    p.add_argument(
        "--min-msgs",
        type=int,
        default=20,
        help="When auto-discovering, only backfill users with >= this many msgs (default 20).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without inserting / embedding.",
    )
    return p.parse_args()


async def main() -> int:
    args = parse_args()

    pg_url = os.environ.get("POSTGRES_URL")
    if not pg_url:
        print("FATAL: POSTGRES_URL not set", file=sys.stderr)
        return 2
    if not args.dry_run and (
        not os.environ.get("AZURE_OPENAI_ENDPOINT") or not os.environ.get("AZURE_OPENAI_KEY")
    ):
        print("FATAL: AZURE_OPENAI_ENDPOINT / KEY not set", file=sys.stderr)
        return 2

    # Import here so module-load errors surface as fatals with a clear stack.
    from insult.core.deep_memory import chunk_text_for_embedding, insert_chunks

    total_chunks_inserted = 0
    started = time.monotonic()

    conn = await asyncpg.connect(pg_url)
    try:
        if args.user_ids:
            users = [(uid, "(explicit)", -1) for uid in args.user_ids]
            print(f"=== Explicit users: {[u[0] for u in users]} ===")
        else:
            users = await discover_active_users(conn, days=args.days, min_msgs=args.min_msgs)
            print(
                f"=== Auto-discovered {len(users)} users with >={args.min_msgs} "
                f"msgs in last {args.days}d ==="
            )
            for uid, name, n in users:
                print(f"  {name} ({uid}): {n} msgs")

        if not users:
            print("Nothing to backfill.")
            return 0

        for user_id, label, _count in users:
            print(f"\n=== {label} ({user_id}) ===")
            msgs = await fetch_user_messages(conn, user_id, days=args.days)
            if not msgs:
                print("  no role='user' messages in window, skipping")
                continue

            first_ts = msgs[0]["timestamp"]
            last_ts = msgs[-1]["timestamp"]
            print(
                f"  pulled {len(msgs)} msgs, "
                f"{_fmt_ts(first_ts)} → {_fmt_ts(last_ts)}"
            )

            doc = "\n\n".join(format_message_block(m) for m in msgs)
            print(f"  doc size: {len(doc):,} chars (~{len(doc.split()):,} words)")

            chunks = chunk_text_for_embedding(doc, chunk_size=400, overlap=50)
            print(f"  produced {len(chunks)} chunks via fi_core.rag")

            if args.dry_run:
                print("  [DRY RUN] skipping embed + insert")
                continue

            source_ref = f"messages:{int(first_ts)}-{int(last_ts)}"
            inserted = await insert_chunks(
                user_id=user_id,
                source_type="message",
                source_ref=source_ref,
                chunks=chunks,
            )
            print(f"  inserted {inserted} new chunks (others were dupes)")
            total_chunks_inserted += inserted

        # Final verification
        rows = await conn.fetch(
            "SELECT user_id, COUNT(*) AS n FROM deep_memory_chunks GROUP BY user_id ORDER BY n DESC"
        )
        print("\n=== deep_memory_chunks after backfill ===")
        for r in rows:
            print(f"  {r['user_id']}: {r['n']} chunks")
    finally:
        await conn.close()

    elapsed = time.monotonic() - started
    print(f"\nDone in {elapsed:.1f}s. Inserted {total_chunks_inserted} new chunks total.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
