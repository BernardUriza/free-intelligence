"""Apply step for the Alex fact restoration. LOCAL-ONLY — does NOT upload.

Run AFTER the dry-run looks correct. Takes a path to a writable copy of
the prod memory.db and inserts the proposed facts inside a single
transaction. Each insertion's excerpt is re-verified against the messages
table at apply time — if any citation has gone missing between dry-run
and apply, the whole transaction aborts.

The companion upload step is intentionally separate. After this script
succeeds against a local copy, the operator must manually:

    1. Inspect the patched DB (sqlite3 ... 'SELECT * FROM user_facts ...')
    2. Upload it to the prod blob with the existing
       `should_force_overwrite` policy (e.g. via az storage blob upload)
    3. Force a container revision restart so the next replica downloads
       the patched blob (or wait for it to download on next boot — the
       new richness guard from v3.7.59 will not block since remote will
       be strictly richer than the in-memory state of the running bot)

Usage:
    python scripts/restore_alex_facts_apply.py /path/to/local_copy.db

Refuses to run if the path appears to be the live storage/memory.db
(matches the relative path "storage/memory.db" — operator can override
with --force if they really mean it; we don't want a typo to corrupt
the running bot's local state)."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# Reuse the canonical proposed-facts list and the helpers — single source of truth.
from restore_alex_facts_dryrun import (  # type: ignore[import-not-found]
    ALEX_USER_ID,
    PROPOSED_FACTS,
    fetch_existing_facts,
    find_message_with_excerpt,
    load_vulnerability_module,
)


def is_live_local_db(p: Path) -> bool:
    """Heuristic: does this path look like the bot's actual live DB?

    We refuse to write to anything that resolves under a `storage/` dir
    inside the repo (where the running bot keeps its in-process DB).
    Operators can override with --force when they know what they're doing.
    """
    parts = {pp.name for pp in p.resolve().parents}
    return "storage" in parts and p.name == "memory.db"


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Alex's restored facts to a local DB copy.")
    parser.add_argument("db_path", type=Path, help="Path to the local DB copy (NOT the live one)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass the live-DB safety check (only if you really mean to write to storage/memory.db).",
    )
    args = parser.parse_args()

    db_path: Path = args.db_path
    if not db_path.exists():
        print(f"ERROR: {db_path} does not exist", file=sys.stderr)
        return 2

    if is_live_local_db(db_path) and not args.force:
        print(
            f"REFUSING: {db_path} looks like the live bot's DB. Re-run with --force "
            "if this is intentional. Otherwise copy it to /tmp first.",
            file=sys.stderr,
        )
        return 4

    vuln = load_vulnerability_module()
    conn = sqlite3.connect(str(db_path))
    try:
        existing_before = fetch_existing_facts(conn, ALEX_USER_ID)
        score_before = vuln.compute_vulnerability_score([{"fact": f["fact"]} for f in existing_before])
        print(f"BEFORE: {len(existing_before)} facts, score={score_before}, "
              f"vulnerable={score_before >= vuln.VULNERABLE_THRESHOLD}")

        # Re-verify every excerpt at apply time (citations may have rotted
        # between the dry-run author's pass and the apply moment).
        for pf in PROPOSED_FACTS:
            match = find_message_with_excerpt(conn, ALEX_USER_ID, pf.source_excerpt)
            if match is None:
                print(
                    f"ABORT: excerpt for fact {pf.fact!r} no longer found in message history.",
                    file=sys.stderr,
                )
                return 3

        # Single transaction so a partial insert can't leave the DB in a
        # half-restored state.
        try:
            conn.execute("BEGIN TRANSACTION")
            for pf in PROPOSED_FACTS:
                conn.execute(
                    "INSERT INTO user_facts (user_id, fact, category, updated_at, source) "
                    "VALUES (?, ?, ?, strftime('%s','now') + 0.0, 'manual')",
                    (ALEX_USER_ID, pf.fact, pf.category),
                )
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"ABORT: transaction failed, rolled back: {e}", file=sys.stderr)
            return 5

        existing_after = fetch_existing_facts(conn, ALEX_USER_ID)
        score_after = vuln.compute_vulnerability_score([{"fact": f["fact"]} for f in existing_after])
        groups_after = vuln.matched_signal_groups([{"fact": f["fact"]} for f in existing_after])
        print(
            f"AFTER:  {len(existing_after)} facts, score={score_after}, "
            f"vulnerable={score_after >= vuln.VULNERABLE_THRESHOLD}, signals={groups_after}"
        )
        if score_after < vuln.VULNERABLE_THRESHOLD:
            print(
                "WARNING: post-apply score is BELOW threshold. The restoration completed "
                "but the scorer no longer treats this user as vulnerable. Investigate.",
                file=sys.stderr,
            )
            return 6

        print()
        print("Restored facts (newly inserted):")
        for f in existing_after:
            if f["id"] not in {x["id"] for x in existing_before}:
                print(f"  +#{f['id']:>5} [{f['category']:<10}] {f['fact']}")

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
