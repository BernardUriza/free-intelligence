"""Roster writes — the daemon owns every write, so the cache never drifts."""

from . import state
from .db import connect


async def add(ip: str, note: str) -> None:
    conn = await connect()
    try:
        await conn.execute(
            "INSERT INTO aire_device (ip, note) VALUES ($1, $2) "
            "ON CONFLICT (ip) DO UPDATE SET note = EXCLUDED.note",
            ip, note or None,
        )
    finally:
        await conn.close()
    state.IPS.add(ip)


async def remove(ip: str) -> None:
    conn = await connect()
    try:
        await conn.execute("DELETE FROM aire_device WHERE ip = $1", ip)
    finally:
        await conn.close()
    state.IPS.discard(ip)
