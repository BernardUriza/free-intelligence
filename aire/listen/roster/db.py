"""Load/refresh the roster from the truth — created as role `aire` ([[write-only-daemon]])."""

from ..applog import _now, append
from ..config import DB_TIMEOUT_S, DSN
from . import state

DDL = ("CREATE TABLE IF NOT EXISTS aire_device (ip text PRIMARY KEY, note text, "
       "added_at timestamptz NOT NULL DEFAULT now());")


async def connect():
    import asyncpg
    return await asyncpg.connect(DSN, timeout=DB_TIMEOUT_S)


async def load() -> None:
    conn = await connect()
    try:
        await conn.execute(DDL)
        state.IPS = {r["ip"] for r in await conn.fetch("SELECT ip FROM aire_device")}
        state.READY = True
    finally:
        await conn.close()


async def refresh() -> None:
    try:
        await load()
    except Exception as exc:  # noqa: BLE001 - a blip must not wipe a good cache
        append(f"{_now()} - WHITELIST-REFRESH-ERROR {exc!r}")
