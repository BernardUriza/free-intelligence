"""The device whitelist (backlog #18): truth in Postgres (`aire_device`), NOT a
file on the mortal droplet disk. `IPS` is a derived cache, updated in lockstep
with ALLOW/REVOKE and refreshed periodically. Reading it is the second
sanctioned exception in [[write-only-daemon]]; the table is created as role
`aire` so the console's reader can see it (the DDL rule)."""

import asyncio

from .applog import _now, append
from .config import DB_TIMEOUT_S, DSN, WHITELIST_ENFORCE
from .tasks import spawn

DDL = ("CREATE TABLE IF NOT EXISTS aire_device (ip text PRIMARY KEY, note text, "
       "added_at timestamptz NOT NULL DEFAULT now());")
IPS: set[str] = set()
READY = False


def enabled() -> bool:
    return bool(DSN)


def ready() -> bool:
    return READY


def allows(ip: str) -> bool:
    return ip in IPS


async def _connect():
    import asyncpg

    return await asyncpg.connect(DSN, timeout=DB_TIMEOUT_S)


async def load() -> None:
    global IPS, READY
    conn = await _connect()
    try:
        await conn.execute(DDL)
        IPS = {r["ip"] for r in await conn.fetch("SELECT ip FROM aire_device")}
        READY = True
    finally:
        await conn.close()


async def refresh() -> None:
    try:
        await load()
    except Exception as exc:  # noqa: BLE001 - a blip must not wipe a good cache
        append(f"{_now()} - WHITELIST-REFRESH-ERROR {exc!r}")


async def add(ip: str, note: str) -> None:
    conn = await _connect()
    try:
        await conn.execute(
            "INSERT INTO aire_device (ip, note) VALUES ($1, $2) "
            "ON CONFLICT (ip) DO UPDATE SET note = EXCLUDED.note", ip, note or None)
    finally:
        await conn.close()
    IPS.add(ip)


async def remove(ip: str) -> None:
    conn = await _connect()
    try:
        await conn.execute("DELETE FROM aire_device WHERE ip = $1", ip)
    finally:
        await conn.close()
    IPS.discard(ip)


async def start() -> None:
    try:
        await load()
        append(f"{_now()} - WHITELIST loaded {len(IPS)} devices "
               f"(enforce={'on' if WHITELIST_ENFORCE else 'off'})")
    except Exception as exc:  # noqa: BLE001 - fail-closed is enforced at the gate
        append(f"{_now()} - WHITELIST-LOAD-ERROR {exc!r}")
        if WHITELIST_ENFORCE:
            append(f"{_now()} - WHITELIST enforce=on but roster UNLOADED "
                   "→ denying all non-loopback until it loads")
    spawn(_refresher())


async def _refresher(interval: int = 60) -> None:
    while True:
        await asyncio.sleep(interval)
        await refresh()
