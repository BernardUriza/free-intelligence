"""accept() → admission → session → teardown. Rejections hang up silently, or
the flood would still reach the log through its own rejections."""

import asyncio

from ..applog import _now, append
from ..guards.conns import CONNS
from ..guards.gate import admit
from .session import session
from .sockets import hangup, peer_info


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    ip, addr, exempt = peer_info(writer)
    if not exempt and not CONNS.acquire(ip):
        return await hangup(writer)
    try:
        if not admit(ip, addr, exempt):
            return await hangup(writer)
        append(f"{_now()} {addr} CONNECT")
        try:
            await session(reader, writer, ip, addr, exempt)
        finally:
            append(f"{_now()} {addr} DISCONNECT")
            await hangup(writer)
    finally:
        if not exempt:
            CONNS.release(ip)
