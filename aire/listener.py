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
import time
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

# The port is open to the internet by design (EC-GPS: devices push, no auth to
# report). That makes the pen a WRITE AMPLIFIER: every accepted line lands in the
# owner's Postgres. Without a ceiling, a stranger with a for-loop fills the disk
# AND inflates the bill. So: a token bucket per peer IP — generous for a real
# device (a keep-alive every 2s is 30/min), fatal for a flood. Loopback is exempt
# (it is us). Enforced per LINE, not per connection: reconnecting does not reset
# the bucket.
RATE_LIMIT_LINES_PER_MIN = int(os.environ.get("AIRE_RATE_LIMIT", "120"))
MAX_LINE_BYTES = 4096

# The device whitelist (backlog #18, learned from Carlos/EC-GPS). Its source of
# truth is a Postgres table `aire_device` in the OWNER's database — NOT a file on
# the mortal droplet disk (that is the exact "the whitelist disappeared" failure).
# Enforcement requires the daemon to READ it: the SECOND sanctioned exception to
# [[write-only-daemon]] (the first is session_store.load for resume), authorized
# by Bernard 2026-07-14. Loopback is always exempt (it is us). Enforcement is OFF
# by default (advisory): flipping AIRE_WHITELIST_ENFORCE=1 turns the gate on —
# with an empty table that denies everyone, so populate it FIRST.
WHITELIST_ENFORCE = os.environ.get("AIRE_WHITELIST_ENFORCE") == "1"

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


class Whitelist:
    """The device roster, deathless in the owner's Postgres (`aire_device`). The
    daemon owns every write (via the ALLOW/REVOKE verbs) so the in-memory cache
    never needs polling — it is updated in lockstep with each write and reloaded
    once on startup. The table is created as role `aire` so the console's reader
    (`aire_reader`) can see the roster ([[write-only-daemon]] DDL rule)."""

    DDL = """
    CREATE TABLE IF NOT EXISTS aire_device (
      ip       text PRIMARY KEY,
      note     text,
      added_at timestamptz NOT NULL DEFAULT now()
    );
    """

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self.ips: set[str] = set()
        self.ready = False

    async def _conn(self):
        import asyncpg

        return await asyncpg.connect(self.dsn)

    async def load(self) -> None:
        conn = await self._conn()
        try:
            await conn.execute(self.DDL)
            rows = await conn.fetch("SELECT ip FROM aire_device")
            self.ips = {r["ip"] for r in rows}
            self.ready = True
        finally:
            await conn.close()

    async def add(self, ip: str, note: str) -> None:
        conn = await self._conn()
        try:
            await conn.execute(
                "INSERT INTO aire_device (ip, note) VALUES ($1, $2) "
                "ON CONFLICT (ip) DO UPDATE SET note = EXCLUDED.note",
                ip,
                note or None,
            )
        finally:
            await conn.close()
        self.ips.add(ip)

    async def remove(self, ip: str) -> None:
        conn = await self._conn()
        try:
            await conn.execute("DELETE FROM aire_device WHERE ip = $1", ip)
        finally:
            await conn.close()
        self.ips.discard(ip)

    def allows(self, ip: str) -> bool:
        return ip in self.ips


WHITELIST = Whitelist(DSN) if DSN else None


def _valid_ip(ip: str) -> bool:
    import ipaddress

    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def append(line: str) -> None:
    append_file(line)
    if PEN is not None:
        PEN.write(line)


class Bucket:
    """Token bucket per peer IP: `RATE_LIMIT_LINES_PER_MIN` lines a minute,
    refilled continuously. State lives per IP (not per connection) so a flooder
    cannot reset it by reconnecting. Idle IPs are evicted so the dict cannot
    become its own memory leak."""

    def __init__(self, rate_per_min: int) -> None:
        self.rate = rate_per_min / 60.0
        self.burst = float(rate_per_min)
        self._tokens: dict[str, float] = {}
        self._seen: dict[str, float] = {}

    def allow(self, ip: str) -> bool:
        now = time.monotonic()
        if len(self._seen) > 10_000:
            cutoff = now - 3600
            for stale in [k for k, t in self._seen.items() if t < cutoff]:
                self._tokens.pop(stale, None)
                self._seen.pop(stale, None)
        last = self._seen.get(ip, now)
        tokens = min(self.burst, self._tokens.get(ip, self.burst) + (now - last) * self.rate)
        self._seen[ip] = now
        if tokens < 1.0:
            self._tokens[ip] = tokens
            return False
        self._tokens[ip] = tokens - 1.0
        return True


BUCKET = Bucket(RATE_LIMIT_LINES_PER_MIN)


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


async def allow_verb(msg: str, addr: str) -> str:
    """`ALLOW <token> <ip> [note]` → add a device to the deathless whitelist. The
    action itself is appended to the log (`ALLOWED-DEVICE`, token redacted) — the
    roster's changes are events like everything else."""
    parts = msg.split(maxsplit=3)
    if len(parts) < 3:
        append(f"{_now()} {addr} ALLOW-REJECTED bad-syntax")
        return "REJECTED usage: ALLOW <token> <ip> [note]"
    token, ip = parts[1], parts[2]
    note = parts[3] if len(parts) > 3 else ""
    if not VERB_TOKEN or not secrets_mod.compare_digest(token, VERB_TOKEN):
        append(f"{_now()} {addr} ALLOW-DENIED")
        return "DENIED"
    if not _valid_ip(ip):
        append(f"{_now()} {addr} ALLOW-REJECTED bad-ip")
        return "REJECTED not an IP"
    if WHITELIST is None:
        return "ERROR no database (whitelist needs AIRE_DATABASE_URL)"
    await WHITELIST.add(ip, note)
    append(f"{_now()} {addr} ALLOWED-DEVICE {ip}")
    return f"ALLOWED {ip}"


async def revoke_verb(msg: str, addr: str) -> str:
    """`REVOKE <token> <ip>` → remove a device from the whitelist."""
    parts = msg.split()
    if len(parts) != 3:
        append(f"{_now()} {addr} REVOKE-REJECTED bad-syntax")
        return "REJECTED usage: REVOKE <token> <ip>"
    token, ip = parts[1], parts[2]
    if not VERB_TOKEN or not secrets_mod.compare_digest(token, VERB_TOKEN):
        append(f"{_now()} {addr} REVOKE-DENIED")
        return "DENIED"
    if WHITELIST is None:
        return "ERROR no database"
    await WHITELIST.remove(ip)
    append(f"{_now()} {addr} REVOKED-DEVICE {ip}")
    return f"REVOKED {ip}"


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    peer = writer.get_extra_info("peername")
    addr = f"{peer[0]}:{peer[1]}" if peer else "?"
    ip = peer[0] if peer else "?"
    exempt = ip.startswith("127.") or ip == "::1"
    if not exempt and not BUCKET.allow(ip):
        # Over budget before saying anything: hang up WITHOUT appending, or the
        # flood would still reach the log through its own rejections.
        writer.close()
        await writer.wait_closed()
        return
    # The whitelist gate (backlog #18). Advisory unless AIRE_WHITELIST_ENFORCE=1.
    # When enforcing, an un-listed device leaves a visible DENIED-DEVICE line —
    # that is the cure for Carlos's failure #1 (a forgotten device goes mute; now
    # you SEE it knocking) — then gets hung up on.
    if (
        WHITELIST_ENFORCE
        and not exempt
        and WHITELIST is not None
        and WHITELIST.ready
        and not WHITELIST.allows(ip)
    ):
        append(f"{_now()} {addr} DENIED-DEVICE")
        writer.close()
        await writer.wait_closed()
        return
    append(f"{_now()} {addr} CONNECT")
    throttled = False
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
            if len(raw) > MAX_LINE_BYTES:
                append(f"{_now()} {addr} OVERSIZED-LINE dropped")
                break
            if not exempt and not BUCKET.allow(ip):
                # ONE line about it (the first), then silence: a rate-limit notice
                # per flooded line would BE the flood.
                if not throttled:
                    append(f"{_now()} {addr} RATE-LIMITED")
                    throttled = True
                break
            msg = raw.decode(errors="replace").rstrip("\r\n")
            if not msg:
                continue
            if msg.startswith("MKDIR"):
                reply = mkdir_verb(msg, addr)
                writer.write((reply + "\n").encode())
                await writer.drain()
            elif msg.startswith("ALLOW "):
                writer.write((await allow_verb(msg, addr) + "\n").encode())
                await writer.drain()
            elif msg.startswith("REVOKE "):
                writer.write((await revoke_verb(msg, addr) + "\n").encode())
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
    if WHITELIST is not None:
        try:
            await WHITELIST.load()
            append(f"{_now()} - WHITELIST loaded {len(WHITELIST.ips)} devices "
                   f"(enforce={'on' if WHITELIST_ENFORCE else 'off'})")
        except Exception as exc:  # noqa: BLE001 - a DB hiccup must not stop the daemon
            append(f"{_now()} - WHITELIST-LOAD-ERROR {exc!r}")
    append(f"{_now()} - LISTENING {HOST}:{PORT}")
    print(f"AIRE listener listening on {HOST}:{PORT} → {LOG}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
