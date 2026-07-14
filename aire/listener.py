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

The first verb (``AIRE_VERB_TOKEN``)
------------------------------------
``MKDIR <token> <name>`` asks the daemon to create a **session casita**: a fresh
workspace folder ``workspaces/{timestamp}_{uuid4}_{name}`` where a future
agent-mode session will live and work (files, runs, everything inside its own
home). Every session is born new — the uniqueness is the point. The verb is
gated by a long token that lives only on Bernard's Mac and in ``/etc/aire/env``;
the port stays internet-open, but ordering requires the family password.
Reporting (plain lines) needs no token, as before. Still no intelligence:
command-as-event — the token-redacted command and its outcome are appended like
any other line, and the client gets a one-line ACK (``CREATED <path>``).

The pen (``AIRE_DATABASE_URL``)
-------------------------------
EC-GPS welds its ``gps_logs`` to the droplet's disk: if the box dies, the memory
dies with it. AIRE's one evolution is ripping the memory out of the mortal body
([[log-is-the-truth]]): when ``AIRE_DATABASE_URL`` is set, every appended line is
ALSO written to an append-only table (``aire_log``) in the owner's Postgres. The
local file stays as the greppable view; the table is the memory with no body to
lose. No DSN → pure EC-GPS mode, file only. Still no intelligence: the same line,
mirrored verbatim, never parsed.
"""

from __future__ import annotations

import asyncio
import os
import re
import secrets as secrets_mod
import uuid
from datetime import datetime, timezone
from pathlib import Path

LOG = Path(os.environ.get("AIRE_LOG", Path(__file__).resolve().parent.parent / "aire.log"))
HOST = os.environ.get("AIRE_HOST", "0.0.0.0")
PORT = int(os.environ.get("AIRE_PORT", "9099"))
DSN = os.environ.get("AIRE_DATABASE_URL", "")
WORKSPACES = Path(
    os.environ.get("AIRE_WORKSPACES", Path(__file__).resolve().parent.parent / "workspaces")
)
VERB_TOKEN = os.environ.get("AIRE_VERB_TOKEN", "")
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS aire_log (
  seq  bigserial PRIMARY KEY,
  at   timestamptz NOT NULL DEFAULT now(),
  line text NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def append_file(line: str) -> None:
    """Append-only: entries are only added, never rewritten (the repo's law,
    [[log-is-the-truth]]). The log IS the truth."""
    with LOG.open("a") as f:
        f.write(line + "\n")
        f.flush()


class Pen:
    """Mirrors appended lines to Postgres, without ever blocking the socket.

    ``write()`` is synchronous and cheap (a queue put); a single background task
    owns the connection, drains the queue in batches, and reconnects with
    backoff. If Postgres is unreachable the queue buffers up to ``maxsize``
    lines and then drops the overflow FOR THE MIRROR ONLY — the local file
    already holds every line, so nothing is lost, only delayed off-body.
    Outages are logged to the file on state change (PEN-DOWN / PEN-UP), not on
    every retry.
    """

    def __init__(self, dsn: str, maxsize: int = 10_000) -> None:
        self.dsn = dsn
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=maxsize)
        self.healthy = False

    def write(self, line: str) -> None:
        try:
            self.queue.put_nowait(line)
        except asyncio.QueueFull:
            pass

    def _mark(self, healthy: bool, detail: str = "") -> None:
        if healthy and not self.healthy:
            append_file(f"{_now()} - PEN-UP mirroring to postgres")
        elif not healthy and self.healthy:
            append_file(f"{_now()} - PEN-DOWN {detail}")
        self.healthy = healthy

    async def run(self) -> None:
        import asyncpg

        delay = 2
        while True:
            try:
                conn = await asyncpg.connect(self.dsn)
                await conn.execute(SCHEMA)
                self._mark(healthy=True)
                delay = 2
                while True:
                    batch = [await self.queue.get()]
                    while len(batch) < 500:
                        try:
                            batch.append(self.queue.get_nowait())
                        except asyncio.QueueEmpty:
                            break
                    try:
                        await conn.executemany(
                            "INSERT INTO aire_log (line) VALUES ($1)",
                            [(line,) for line in batch],
                        )
                    except Exception:
                        for line in batch:
                            self.write(line)
                        raise
            except Exception as exc:
                self._mark(healthy=False, detail=repr(exc))
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)


PEN = Pen(DSN) if DSN else None


def append(line: str) -> None:
    append_file(line)
    if PEN is not None:
        PEN.write(line)


def mkdir_verb(msg: str, addr: str) -> str:
    """The first verb. `MKDIR <token> <name>` → a fresh session casita under
    ``workspaces/``, named ``{timestamp}_{uuid4}_{name}`` — every session is
    born new, never reused. Command-as-event: the (token-REDACTED) command and
    its result are appended to the log like any other line; the raw token never
    touches the log, the file, or Postgres. The reply is the ACK the client
    reads back, EC-GPS style."""
    parts = msg.split()
    if len(parts) != 3:
        append(f"{_now()} {addr} MKDIR-REJECTED bad-syntax")
        return "REJECTED usage: MKDIR <token> <name>"
    _, token, name = parts
    if not VERB_TOKEN or not secrets_mod.compare_digest(token, VERB_TOKEN):
        append(f"{_now()} {addr} MKDIR-DENIED")
        return "DENIED"
    if not NAME_RE.match(name):
        append(f"{_now()} {addr} MKDIR-REJECTED bad-name")
        return "REJECTED name must match [A-Za-z0-9_-]{1,64}"
    append(f"{_now()} {addr} MKDIR {name}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = WORKSPACES / f"{stamp}_{uuid.uuid4()}_{name}"
    try:
        path.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        append(f"{_now()} - MKDIR-ERROR {exc!r}")
        return "ERROR could not create"
    append(f"{_now()} - FOLDER-CREATED {path}")
    return f"CREATED {path}"


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    peer = writer.get_extra_info("peername")
    addr = f"{peer[0]}:{peer[1]}" if peer else "?"
    append(f"{_now()} {addr} CONNECT")
    try:
        while True:
            try:
                raw = await reader.readline()
            except ValueError:
                # A line longer than asyncio's 64KiB buffer with no newline. The
                # port is open to the internet by design (EC-GPS: devices push),
                # so a peer that never sends \n is EXPECTED input, not a bug —
                # drop that peer instead of letting the exception escape the task
                # and print an unhandled traceback into the journal.
                append(f"{_now()} {addr} OVERLONG-LINE dropped")
                break
            if not raw:  # the device closed the connection
                break
            msg = raw.decode(errors="replace").rstrip("\r\n")
            if not msg:
                continue
            if msg.startswith("MKDIR"):
                reply = mkdir_verb(msg, addr)
                writer.write((reply + "\n").encode())
                await writer.drain()
            else:
                append(f"{_now()} {addr} {msg}")
    finally:
        append(f"{_now()} {addr} DISCONNECT")
        writer.close()
        await writer.wait_closed()


async def main() -> None:
    server = await asyncio.start_server(handle, HOST, PORT)
    if PEN is not None:
        asyncio.create_task(PEN.run())
    append(f"{_now()} - LISTENING {HOST}:{PORT}")
    print(f"AIRE listener listening on {HOST}:{PORT} → {LOG}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
