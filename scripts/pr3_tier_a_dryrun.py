"""PR-3 Tier A — read-only dry-run against prod.

Pulls every live auto fact, runs `build_near_miss_plan` PARTITIONED BY
principal_id (so a fold can never cross owners), and prints the audit report
the coagent asked for. SELECT-only: no DELETE, no UPDATE, no side effects.

Conn string comes from env `PR3_PG_URL` (never hardcoded — secrets rule).
Run:  PR3_PG_URL="postgresql://..." python scripts/pr3_tier_a_dryrun.py
"""

from __future__ import annotations

import asyncio
import os
import random
import re
import unicodedata

import asyncpg

from personas.insult.core.near_miss_fold import build_near_miss_plan

random.seed(20260614)

_DIGITS = re.compile(r"\d")


def _digit_seq(s: str) -> str:
    return "".join(_DIGITS.findall(s))


def _mechanical_reasons(survivor: str, loser: str) -> list[str]:
    """Which orthographic transforms separate two same-key facts (audit aid)."""

    def case(x: str) -> str:
        return x.lower()

    def ws(x: str) -> str:
        return " ".join(x.split())

    def acc(x: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFKD", x) if not unicodedata.combining(c))

    def thou(x: str) -> str:
        return re.sub(r"(?<=\d)[.,](?=\d{3}(?:\D|$))", "", x)

    def punc(x: str) -> str:
        return " ".join(re.sub(r"[^\w\s]", " ", x).split())

    a, b = survivor, loser
    applied: list[str] = []
    for name, fn in [("case", case), ("whitespace", ws), ("accent", acc), ("thousands", thou), ("punctuation", punc)]:
        if a == b:
            break
        na, nb = fn(a), fn(b)
        if na != a or nb != b:
            applied.append(name)
        a, b = na, nb
    if a != b:
        applied.append("UNEXPLAINED")
    return applied or ["identical"]


async def main() -> None:
    url = os.environ["PR3_PG_URL"]
    conn = await asyncpg.connect(url)
    try:
        rows = await conn.fetch(
            "SELECT id, principal_id, fact FROM principal_facts "
            "WHERE deleted_at IS NULL AND source='auto' ORDER BY principal_id, id"
        )
    finally:
        await conn.close()

    by_principal: dict[str, list[dict]] = {}
    id_to_principal: dict[int, str] = {}
    for r in rows:
        by_principal.setdefault(r["principal_id"], []).append({"id": r["id"], "fact": r["fact"]})
        id_to_principal[r["id"]] = r["principal_id"]

    total_rows = len(rows)
    all_groups: list[dict] = []  # {principal, survivor_id, survivor_fact, losers:[{id,fact,reasons}]}
    digit_violations: list[tuple] = []
    cross_owner_violations = 0

    for principal, facts in by_principal.items():
        plan = build_near_miss_plan(facts)
        by_id = {f["id"]: f["fact"] for f in facts}
        # reconstruct groups from the plan (NOOP survivor followed by its DELETEs)
        cur: dict | None = None
        for op in plan:
            if op["op"] == "NOOP":
                if cur:
                    all_groups.append(cur)
                cur = {
                    "principal": principal,
                    "survivor_id": op["id"],
                    "survivor_fact": by_id[op["id"]],
                    "losers": [],
                }
            elif op["op"] == "DELETE":
                assert cur is not None
                loser_fact = by_id[op["id"]]
                reasons = _mechanical_reasons(cur["survivor_fact"], loser_fact)
                cur["losers"].append({"id": op["id"], "fact": loser_fact, "reasons": reasons})
                if _digit_seq(cur["survivor_fact"]) != _digit_seq(loser_fact):
                    digit_violations.append((cur["survivor_id"], op["id"]))
        if cur:
            all_groups.append(cur)

    # cross-owner is impossible by construction (per-principal loop); verify it
    # post-hoc against the global id->principal map (don't just assert it).
    for g in all_groups:
        owners = {id_to_principal[g["survivor_id"]]} | {id_to_principal[ls["id"]] for ls in g["losers"]}
        if len(owners) > 1:
            cross_owner_violations += 1

    loser_rows = sum(len(g["losers"]) for g in all_groups)
    candidate_groups = len(all_groups)

    print("=" * 70)
    print("PR-3 Tier A — DRY-RUN (read-only, per-principal, no LLM, no cosine)")
    print("=" * 70)
    print(f"total_auto_rows      = {total_rows}")
    print(f"candidate_groups     = {candidate_groups}")
    print(f"candidate_loser_rows = {loser_rows}")
    print(f"rows_after_fold      = {total_rows - loser_rows}")
    pct = (loser_rows / total_rows * 100) if total_rows else 0
    print(f"reduction            = {pct:.1f}%")
    print()
    print("-- breakdown por principal --")
    for principal, facts in by_principal.items():
        g = [x for x in all_groups if x["principal"] == principal]
        losers = sum(len(x["losers"]) for x in g)
        print(f"  {principal}: rows={len(facts)} groups={len(g)} losers={losers} -> after={len(facts) - losers}")
    print()
    print("-- INVARIANTES DE SEGURIDAD --")
    print(f"  cross_owner_folds (debe ser 0, por construcción per-principal) = {cross_owner_violations}")
    print(f"  digit_loss_violations (debe ser 0)                             = {len(digit_violations)}")
    if digit_violations:
        print(f"    !!! {digit_violations[:10]}")
    unexplained = [g for g in all_groups for ls in g["losers"] if "UNEXPLAINED" in ls["reasons"]]
    print(f"  unexplained_losers (debe ser 0)                                = {len(unexplained)}")
    print()
    print("-- TOP 20 grupos por tamaño (survivor + n losers) --")
    for g in sorted(all_groups, key=lambda x: len(x["losers"]), reverse=True)[:20]:
        print(f"  [{len(g['losers']) + 1} rows] {g['survivor_fact'][:80]!r}")
    print()
    print("-- 20 muestras aleatorias survivor/loser (con razón mecánica) --")
    flat = [(g["survivor_fact"], ls["fact"], ls["reasons"]) for g in all_groups for ls in g["losers"]]
    for s, lo, reasons in random.sample(flat, min(20, len(flat))):
        print(f"  reasons={','.join(reasons)}")
        print(f"    survivor: {s[:90]!r}")
        print(f"    loser   : {lo[:90]!r}")


if __name__ == "__main__":
    asyncio.run(main())
