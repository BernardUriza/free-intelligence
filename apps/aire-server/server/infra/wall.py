"""The reader wall, as code — the half of the kill test that was never written.

Provisioning is meticulous about the DROPLET: every knob in `/etc/aire/env` is
composed from `~/.secrets/` so destroying the box and re-provisioning resurrects
the full daemon. But the droplet is the MORTAL half. The immortal half — the
owner's Postgres, where the memory actually lives — was never provisioned at
all. The two roles and one default-ACL that make the whole two-halves
architecture real (`server/.claude/rules/write-only-daemon.md`: the daemon holds
the pen, the front holds only `aire_reader`) existed on 2026-08-22 for exactly
one reason: someone typed them into psql on 2026-07-13. The only record of that
was a COMMENT inside `~/.secrets/aire-postgres-readonly.txt`.

So: rebuild the Postgres server, restore from a backup, or drop `aire_reader` by
hand, and nothing in this repo could put the wall back. The front would go blind,
and the most likely repair under pressure is handing it the pen — which is the
one failure the rule exists to prevent.

Run at provision time, never by the serving daemon. Its reads are catalog reads
that VERIFY a grant; they render nothing and gate a write, the same family as the
roster load. Idempotent: safe on every provision.

    python3 infra/wall.py            # grant what `aire` may, then verify
    python3 infra/wall.py --check    # verify only (no grants) — for a watchdog
"""

from __future__ import annotations

import asyncio
import os
import sys

READER = "aire_reader"
# What `aire` is allowed to run itself: it OWNS the tables, so it may grant on
# them, and it may set its own default privileges. Creating the role needs an
# admin — see ADMIN_SQL.
GRANTS = (
    f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {READER}",
    f"ALTER DEFAULT PRIVILEGES FOR ROLE aire IN SCHEMA public "
    f"GRANT SELECT ON TABLES TO {READER}",
)
ADMIN_SQL = f"""
-- Run ONCE as the server's admin (devadmin on development-pg-n66dz); the
-- daemon's own role has neither SUPERUSER nor CREATEROLE, so it cannot.
CREATE ROLE {READER} LOGIN PASSWORD '<pick one, then store it in
                                     ~/.secrets/aire-postgres-readonly.txt>';
GRANT CONNECT ON DATABASE aire TO {READER};
GRANT USAGE ON SCHEMA public TO {READER};
-- Then re-run infra/wall.py; it does the rest and proves it.
"""


async def _reader_exists(conn) -> bool:
    return bool(await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", READER))


async def _blind_tables(conn) -> list[str]:
    """Tables the daemon owns that the waiter cannot read. Any hit means the
    front is blind to that table — a silent 500 on the console, never a log."""
    rows = await conn.fetch(
        "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relkind = 'r' "
        "AND NOT has_table_privilege($1, c.oid, 'SELECT') ORDER BY 1", READER)
    return [r[0] for r in rows]


async def _default_acl(conn) -> bool:
    """The grant that covers tables that DO NOT EXIST YET. Without it every new
    table the daemon creates is born invisible to the front — the failure only
    shows up on the next feature, which is why it must be asserted, not assumed."""
    return bool(await conn.fetchval(
        "SELECT 1 FROM pg_default_acl d JOIN pg_roles r ON r.oid = d.defaclrole "
        "WHERE r.rolname = 'aire' AND d.defaclnamespace = 'public'::regnamespace "
        "AND d.defaclobjtype = 'r' AND array_to_string(d.defaclacl, ',') LIKE $1",
        f"%{READER}=r%"))


async def main(check_only: bool) -> int:
    import asyncpg

    dsn = os.environ.get("AIRE_DATABASE_URL", "")
    if not dsn:
        print("wall: AIRE_DATABASE_URL is empty — nothing to check", file=sys.stderr)
        return 1
    conn = await asyncpg.connect(dsn, timeout=15)
    try:
        if not await _reader_exists(conn):
            print(f"wall: role {READER} DOES NOT EXIST — the front has no credential "
                  f"and the CQRS wall is gone.{ADMIN_SQL}", file=sys.stderr)
            return 1
        if not check_only:
            for statement in GRANTS:
                await conn.execute(statement)
        return _verdict(await _blind_tables(conn), await _default_acl(conn))
    finally:
        await conn.close()


def _verdict(blind: list[str], future_ok: bool) -> int:
    if blind:
        print(f"wall: {READER} cannot SELECT {', '.join(blind)} — the front is blind "
              "to them", file=sys.stderr)
    if not future_ok:
        print(f"wall: no default privilege for {READER} — every table the daemon "
              "creates from now on is born invisible to the front", file=sys.stderr)
    if blind or not future_ok:
        return 1
    print(f"wall: {READER} reads every table the pen owns, and every future one")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main("--check" in sys.argv)))
