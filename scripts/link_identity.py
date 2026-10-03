"""Liga una identidad de superficie a un principal canónico (F2, 2026-09-27).

La tabla `principal_identities` es el puente entre "Bernard en Discord"
(snowflake) y "Bernard en og118" (`sub` de Auth0). Se llena SOLO así, a mano y
con intención — nunca inferida por el runner. El `sub` sale de KQL: el primer
turno desde una superficie nueva loguea `principal_identity_unlinked` con el id
tal cual llegó.

    python scripts/link_identity.py list
    python scripts/link_identity.py link --surface og118 --external-id 'auth0|abc' --principal 907264175246569543
    python scripts/link_identity.py unlink --surface og118 --external-id 'auth0|abc'

`POSTGRES_URL` viene del env (consúmela a variable, nunca la imprimas):
    export POSTGRES_URL=$(cat ~/.secrets/discord-bot-postgres-url.txt)
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
from pathlib import Path

import asyncpg

# `python scripts/link_identity.py` pone scripts/ en sys.path, no la raíz del repo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona_runner.engine.principal_identity import _DDL, looks_like_snowflake  # noqa: E402


async def _connect() -> asyncpg.Connection:
    url = os.environ.get("POSTGRES_URL")
    if not url:
        sys.exit("POSTGRES_URL no está en el env")
    conn = await asyncpg.connect(url)
    await conn.execute(_DDL)
    return conn


async def cmd_list(_args: argparse.Namespace) -> None:
    conn = await _connect()
    try:
        rows = await conn.fetch(
            "SELECT surface, external_id, principal_id, linked_at, linked_by "
            "FROM principal_identities ORDER BY principal_id, surface"
        )
    finally:
        await conn.close()
    if not rows:
        print("(sin identidades ligadas)")
        return
    for r in rows:
        print(f"{r['principal_id']}  <-  {r['surface']}:{r['external_id']}  ({r['linked_at']:%Y-%m-%d}, {r['linked_by']})")


async def cmd_link(args: argparse.Namespace) -> None:
    if not looks_like_snowflake(args.principal):
        # Hoy todo principal canónico es el snowflake bajo el que ya vive la
        # memoria; ligar hacia otro formato crearía un principal nuevo por accidente.
        sys.exit(f"--principal debe ser un principal existente (snowflake), no {args.principal!r}")
    conn = await _connect()
    try:
        existing = await conn.fetchval(
            "SELECT principal_id FROM principal_identities WHERE surface = $1 AND external_id = $2",
            args.surface,
            args.external_id,
        )
        if existing and existing != args.principal and not args.force:
            sys.exit(f"{args.surface}:{args.external_id} ya apunta a {existing}; usa --force para re-ligar")
        n_facts = await conn.fetchval(
            "SELECT count(*) FROM principal_facts WHERE principal_id = $1 AND deleted_at IS NULL", args.principal
        )
        await conn.execute(
            "INSERT INTO principal_identities (surface, external_id, principal_id, linked_by) "
            "VALUES ($1, $2, $3, $4) "
            "ON CONFLICT (surface, external_id) DO UPDATE SET principal_id = $3, linked_at = now(), linked_by = $4",
            args.surface,
            args.external_id,
            args.principal,
            getpass.getuser(),
        )
    finally:
        await conn.close()
    print(f"ligado: {args.surface}:{args.external_id} -> {args.principal} ({n_facts} facts vivos detrás)")


async def cmd_unlink(args: argparse.Namespace) -> None:
    conn = await _connect()
    try:
        status = await conn.execute(
            "DELETE FROM principal_identities WHERE surface = $1 AND external_id = $2",
            args.surface,
            args.external_id,
        )
    finally:
        await conn.close()
    print(status)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    link = sub.add_parser("link")
    link.add_argument("--surface", required=True)
    link.add_argument("--external-id", required=True)
    link.add_argument("--principal", required=True)
    link.add_argument("--force", action="store_true", help="re-ligar un external_id que ya apunta a otro principal")
    link.set_defaults(fn=cmd_link)
    unlink = sub.add_parser("unlink")
    unlink.add_argument("--surface", required=True)
    unlink.add_argument("--external-id", required=True)
    unlink.set_defaults(fn=cmd_unlink)
    args = p.parse_args()
    asyncio.run(args.fn(args))


if __name__ == "__main__":
    main()
