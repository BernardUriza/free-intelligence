"""Per-connection loop: reports are appended; verbs are dispatched and ACKed.
One RATE-LIMITED line, then silence — a notice per flooded line IS the flood."""

import asyncio

from ..applog import _now, append
from ..guards.bucket import BUCKET
from ..verbs import dispatch
from .lines import read_line


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
