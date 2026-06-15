"""PR-3 Tier A — APPLY against prod (soft-delete the orthographic losers).

Mirrors FactsRepository.apply_consolidation_plan's DELETE + audit semantics
(read from personas/insult/core/memory/repositories/facts.py): soft-delete each
loser (deleted_at = run_ts, recoverable 90 days) and write one fact_consolidation_log
row per op, all in ONE transaction so principal_facts and the audit log can never
disagree.

Decision is build_near_miss_plan PARTITIONED BY principal_id — identical to the
dry-run, so this touches EXACTLY the rows the dry-run reported. In-script
invariant guard re-checks digit-preservation and same-owner before any write and
ABORTS the whole run on any violation.

SELECT + UPDATE(soft-delete) + INSERT(audit) only. No hard delete. No merges
(NOOP survivors keep their row + embedding untouched).

Conn from env `PR3_PG_URL`. Run:
  PR3_PG_URL="postgresql://..." PYTHONPATH=. python scripts/pr3_tier_a_apply.py
"""

from __future__ import annotations

import asyncio
import os
import re
import time

import asyncpg

from personas.insult.core.near_miss_fold import build_near_miss_plan

_DIGITS = re.compile(r"\d")


def _digit_seq(s: str) -> str:
    return "".join(_DIGITS.findall(s))


async def main() -> None:
    url = os.environ["PR3_PG_URL"]
    conn = await asyncpg.connect(url)
    run_ts = time.time()
    try:
        rows = await conn.fetch(
            "SELECT id, principal_id, fact FROM principal_facts "
            "WHERE deleted_at IS NULL AND source='auto' ORDER BY principal_id, id"
        )
        by_principal: dict[str, list[dict]] = {}
        id_owner: dict[int, str] = {}
        for r in rows:
            by_principal.setdefault(r["principal_id"], []).append({"id": r["id"], "fact": r["fact"]})
            id_owner[r["id"]] = r["principal_id"]

        live_before = len(rows)

        # Build the full op list (per-principal) and GUARD invariants first.
        deletes: list[tuple[int, str, str]] = []  # (loser_id, loser_text, reason)
        noops: list[tuple[int, str]] = []  # (survivor_id, survivor_text)
        for _principal, facts in by_principal.items():
            plan = build_near_miss_plan(facts)
            by_id = {f["id"]: f["fact"] for f in facts}
            cur_survivor: int | None = None
            for op in plan:
                if op["op"] == "NOOP":
                    cur_survivor = op["id"]
                    noops.append((op["id"], by_id[op["id"]]))
                elif op["op"] == "DELETE":
                    loser_id = op["id"]
                    # INVARIANT GUARDS — abort on any violation before writing.
                    if id_owner[loser_id] != id_owner[cur_survivor]:
                        raise SystemExit(f"ABORT cross-owner: loser {loser_id} vs survivor {cur_survivor}")
                    if _digit_seq(by_id[loser_id]) != _digit_seq(by_id[cur_survivor]):
                        raise SystemExit(f"ABORT digit-loss: loser {loser_id} vs survivor {cur_survivor}")
                    deletes.append((loser_id, by_id[loser_id], op.get("reason", "near_miss_orthographic_variant")))

        print(f"live_auto_before = {live_before}")
        print(f"groups           = {len(noops)}")
        print(f"to_soft_delete   = {len(deletes)}")
        print("invariant guards = PASSED (0 cross-owner, 0 digit-loss)")

        # APPLY — single transaction: soft-delete losers + audit every op.
        async with conn.transaction():
            for loser_id, loser_text, reason in deletes:
                await conn.execute(
                    "UPDATE principal_facts SET deleted_at = $1 WHERE id = $2 AND deleted_at IS NULL",
                    run_ts,
                    loser_id,
                )
                await conn.execute(
                    "INSERT INTO fact_consolidation_log "
                    "(run_ts, principal_id, fact_id_before, fact_id_after, op, reason, "
                    "fact_text_before, fact_text_after) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                    run_ts,
                    id_owner[loser_id],
                    loser_id,
                    None,
                    "DELETE",
                    reason,
                    loser_text,
                    None,
                )
            for survivor_id, survivor_text in noops:
                await conn.execute(
                    "INSERT INTO fact_consolidation_log "
                    "(run_ts, principal_id, fact_id_before, fact_id_after, op, reason, "
                    "fact_text_before, fact_text_after) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                    run_ts,
                    id_owner[survivor_id],
                    survivor_id,
                    survivor_id,
                    "NOOP",
                    "near_miss_survivor",
                    survivor_text,
                    survivor_text,
                )

        live_after = await conn.fetchval(
            "SELECT count(*) FROM principal_facts WHERE deleted_at IS NULL AND source='auto'"
        )
        audit_rows = await conn.fetchval("SELECT count(*) FROM fact_consolidation_log WHERE run_ts = $1", run_ts)
        print(f"live_auto_after  = {live_after}")
        print(f"delta            = {live_before - live_after} (expected {len(deletes)})")
        print(f"audit_rows       = {audit_rows} (expected {len(deletes) + len(noops)})")
        print("OK" if (live_before - live_after) == len(deletes) else "MISMATCH — investigate")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
