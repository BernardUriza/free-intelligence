"""AIRE — the daemon that listens. NO intelligence.

The eternal chassis, bare: `accept()` → read lines → **append to the log**. It is
the EC-GPS daemon —an always-on service listening on a TCP port— without the Perl
and without the brain. The AI (engine/render/store, still in the repo) sits
AFTER, between the `accept()` and the append. Today it isn't here: on purpose.

Every line arriving from a device is appended, as-is, to an **append-only** log
(`aire.log`), with a timestamp and the peer. Greppable, which is the whole point:

    tail -f aire.log | grep KEEPALIVE      # the heartbeats, live
    grep MESSAGE aire.log                   # the device's random messages

The day this lives on a cloud box, "SSH in and grep" is literally that — the
EC-GPS experience, recreated.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

LOG = Path(os.environ.get("AIRE_LOG", Path(__file__).resolve().parent.parent / "aire.log"))
HOST = os.environ.get("AIRE_HOST", "0.0.0.0")
PORT = int(os.environ.get("AIRE_PORT", "9099"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def append(line: str) -> None:
    """Append-only: entries are only added, never rewritten (the repo's law,
    [[log-is-the-truth]]). The log IS the truth."""
    with LOG.open("a") as f:
        f.write(line + "\n")
        f.flush()


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    peer = writer.get_extra_info("peername")
    addr = f"{peer[0]}:{peer[1]}" if peer else "?"
    append(f"{_now()} {addr} CONNECT")
    try:
        while True:
            raw = await reader.readline()
            if not raw:  # the device closed the connection
                break
            msg = raw.decode(errors="replace").rstrip("\r\n")
            if msg:
                append(f"{_now()} {addr} {msg}")
    finally:
        append(f"{_now()} {addr} DISCONNECT")
        writer.close()


async def main() -> None:
    server = await asyncio.start_server(handle, HOST, PORT)
    append(f"{_now()} - LISTENING {HOST}:{PORT}")
    print(f"AIRE listener listening on {HOST}:{PORT} → {LOG}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
