"""The socket surface: accept() → admission → session → teardown. Rejections
hang up silently, or the flood would still reach the log through its own
rejections (one RATE-LIMITED line, then silence)."""

import asyncio

from .applog import _now, append
from .config import MAX_LINE_BYTES
from .guards import BUCKET, CONNS, admit
from .verbs import dispatch


def peer_info(writer: asyncio.StreamWriter) -> tuple[str, str, bool]:
    peer = writer.get_extra_info("peername")
    addr = f"{peer[0]}:{peer[1]}" if peer else "?"
    ip = peer[0] if peer else "?"
    return ip, addr, ip.startswith("127.") or ip == "::1"


async def hangup(writer: asyncio.StreamWriter) -> None:
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:  # noqa: BLE001 - teardown of a dead socket is best-effort
        pass


async def read_line(reader: asyncio.StreamReader, addr: str) -> str | None:
    """None → close the connection; '' → skip; text → process."""
    try:
        raw = await reader.readline()
    except ValueError:
        append(f"{_now()} {addr} OVERLONG-LINE dropped")
        return None
    if not raw:
        return None
    if len(raw) > MAX_LINE_BYTES:
        append(f"{_now()} {addr} OVERSIZED-LINE dropped")
        return None
    # NUL is valid UTF-8 but Postgres text cannot hold it — the 6-day poison
    # pill (docs/listener-doctrine.md). Neutralize it at the mouth.
    return raw.decode(errors="replace").replace("\x00", "�").rstrip("\r\n")


async def session(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                  ip: str, addr: str, exempt: bool) -> None:
    while True:
        msg = await read_line(reader, addr)
        if msg is None:
            return
        if not exempt and not BUCKET.allow(ip):
            append(f"{_now()} {addr} RATE-LIMITED")
            return
        if not msg:
            continue
        reply = await dispatch(msg, addr)
        if reply is None:
            append(f"{_now()} {addr} {msg}")
        else:
            writer.write((reply + "\n").encode())
            await writer.drain()


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
