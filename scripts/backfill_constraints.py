"""Backfill the reserved `constraint` category over facts that already exist.

The invariants pipeline (`khimeras_shared/constraints.py`) only sees facts tagged
`category='constraint'`. Every fact written before 2026-07-23 predates the tag,
so the load-bearing ones — vegan, atheist, does-not-drive — sit under `personal`
or `preferences` and never ride the guidance. This promotes them.

Deliberately CONSERVATIVE and reversible:

- It only ever runs `UPDATE ... SET category='constraint'`. No deletes, no
  rewrites of `fact`, no touching `source`. (`save_facts(subset)` is a
  hard-delete in disguise — the 2026-06-03 P0 — so this never goes near it.)
- Dry-run by default: prints what it WOULD promote, changes nothing.
- Every promotion prints the previous category, so a revert is a one-liner.
- Patterns are anchored and narrow. A store full of fake invariants drowns the
  real ones, which is the exact failure this pipeline exists to prevent.

    python scripts/backfill_constraints.py <principal_id>            # dry run
    python scripts/backfill_constraints.py <principal_id> --apply    # promote

`POSTGRES_URL` comes from the env, or from the persona-gateway secret:
    export POSTGRES_URL=$(az containerapp secret show --name persona-gateway \
        -g insult-rg --secret-name postgres-url --query value -o tsv)
"""

from __future__ import annotations

import asyncio
import os
import re
import sys

import asyncpg

# Anchored on the CLAIM, not the topic. "rechaza la explotación animal basada en
# ... religión" is an opinion about ethics; "es ateo" is an invariant. The
# difference is what keeps this from promoting 30 religion-adjacent facts.
# A fact ABOUT someone else's invariant is not the user's. "Sabe que Bunbury de
# Héroes del Silencio es vegano" matches `es vegano` and is trivia — promoting it
# would put another man's diet in Bernard's hard-restrictions block.
THIRD_PARTY = re.compile(r"\b(?:sabe|conoce|le consta|se enter[óo]|escuch[óo]|ley[óo])\s+que\b", re.IGNORECASE)

PATTERNS: list[tuple[str, str]] = [
    (r"\bes ate[oa]\b|\bsoy ate[oa]\b|\bate[ií]smo\b", "worldview"),
    (r"\bes vegan[oa]\b|\bsoy vegan[oa]\b|\bes vegetarian[oa]\b", "diet"),
    (r"\bcel[ií]ac[oa]\b|\bintolerante a\b|\bal[ée]rgic[oa] a\b", "medical"),
    (r"\bno (?:tiene|cuenta con) licencia\b|\bno sabe manejar\b|\bno maneja\b", "limit"),
    (r"\bno bebe\b|\bno toma alcohol\b|\bno fuma\b|\bes abstemi[oa]\b", "limit"),
    (r"\bno habla con su\b|\bsin contacto con su\b|\bdistanciad[oa] de su\b", "estrangement"),
]


async def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    principal_id = sys.argv[1]
    apply = "--apply" in sys.argv
    url = os.environ.get("POSTGRES_URL", "")
    if not url:
        print("POSTGRES_URL not set — see the module docstring.", file=sys.stderr)
        return 2

    conn = await asyncpg.connect(url)
    try:
        rows = await conn.fetch(
            "SELECT id, category, source, fact FROM principal_facts "
            "WHERE principal_id = $1 AND deleted_at IS NULL AND category <> 'constraint' "
            "ORDER BY id",
            principal_id,
        )
        hits = []
        skipped_third_party = 0
        for row in rows:
            if THIRD_PARTY.search(row["fact"]):
                skipped_third_party += 1
                continue
            for pattern, kind in PATTERNS:
                if re.search(pattern, row["fact"], re.IGNORECASE):
                    hits.append((row["id"], row["category"], row["source"], kind, row["fact"]))
                    break

        already = await conn.fetchval(
            "SELECT count(*) FROM principal_facts WHERE principal_id = $1 "
            "AND deleted_at IS NULL AND category = 'constraint'",
            principal_id,
        )
        print(
            f"scanned={len(rows)} already_constraint={already} "
            f"candidates={len(hits)} skipped_third_party={skipped_third_party}\n"
        )
        for fact_id, category, source, kind, fact in hits:
            print(f"  [{kind:12}] id={fact_id} {source}/{category} → constraint")
            print(f"               {fact[:120]}")

        if not hits:
            print("\nnothing to promote.")
            return 0
        if not apply:
            print("\nDRY RUN — nothing written. Re-run with --apply to promote.")
            return 0

        ids = [h[0] for h in hits]
        updated = await conn.execute(
            "UPDATE principal_facts SET category = 'constraint' WHERE id = ANY($1::bigint[])",
            ids,
        )
        print(f"\napplied: {updated}")
        print("revert with:  UPDATE principal_facts SET category='<old>' WHERE id IN (...)")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
