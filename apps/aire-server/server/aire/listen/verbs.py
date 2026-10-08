"""The verbs — the daemon's write-command contract (device-verb-protocol rule).
Token-gated (constant-time), command-as-event: the token-REDACTED command and
its outcome are appended like any other line; the raw token never touches the
log, the file, or Postgres. The reply is the one-line ACK the client reads.

TWO lines per accepted verb, never one: the command when it is accepted, the
outcome when it lands. MKDIR always did; ALLOW and REVOKE only logged success,
so a Postgres blip took the whole attempt out of the append-only log — no
command, no failure, and an ACK the client never received because the exception
walked out through the connection handler. An unrecorded write is the one thing
the log exists to make impossible (backlog #40)."""

import ipaddress
import secrets
import uuid
from datetime import datetime, timezone

from . import roster
from .applog import _now, append
from .config import NAME_RE, VERB_TOKEN, WORKSPACES


def token_ok(token: str) -> bool:
    return bool(VERB_TOKEN) and secrets.compare_digest(token, VERB_TOKEN)


def valid_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def mkdir_verb(msg: str, addr: str) -> str:
    parts = msg.split()
    if len(parts) != 3:
        append(f"{_now()} {addr} MKDIR-REJECTED bad-syntax")
        return "REJECTED usage: MKDIR <token> <name>"
    if not token_ok(parts[1]):
        append(f"{_now()} {addr} MKDIR-DENIED")
        return "DENIED"
    if not NAME_RE.match(parts[2]):
        append(f"{_now()} {addr} MKDIR-REJECTED bad-name")
        return "REJECTED name must match [A-Za-z0-9_-]{1,64}"
    append(f"{_now()} {addr} MKDIR {parts[2]}")
    path = WORKSPACES / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{uuid.uuid4()}_{parts[2]}"
    try:
        path.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        append(f"{_now()} - MKDIR-ERROR {exc!r}")
        return "ERROR could not create"
    append(f"{_now()} - FOLDER-CREATED {path}")
    return f"CREATED {path}"


async def allow_verb(msg: str, addr: str) -> str:
    parts = msg.split(maxsplit=3)
    if len(parts) < 3:
        append(f"{_now()} {addr} ALLOW-REJECTED bad-syntax")
        return "REJECTED usage: ALLOW <token> <ip> [note]"
    token, ip = parts[1], parts[2]
    if not token_ok(token):
        append(f"{_now()} {addr} ALLOW-DENIED")
        return "DENIED"
    if not valid_ip(ip):
        append(f"{_now()} {addr} ALLOW-REJECTED bad-ip")
        return "REJECTED not an IP"
    if not roster.enabled():
        append(f"{_now()} {addr} ALLOW-ERROR no-database")
        return "ERROR no database (whitelist needs AIRE_DATABASE_URL)"
    append(f"{_now()} {addr} ALLOW {ip}")
    try:
        await roster.add(ip, parts[3] if len(parts) > 3 else "")
    except Exception as exc:  # noqa: BLE001 - any failure, one visible outcome
        append(f"{_now()} {addr} ALLOW-ERROR {ip} {exc!r}")
        return "ERROR roster write failed"
    append(f"{_now()} {addr} ALLOWED-DEVICE {ip}")
    return f"ALLOWED {ip}"


async def revoke_verb(msg: str, addr: str) -> str:
    parts = msg.split()
    if len(parts) != 3:
        append(f"{_now()} {addr} REVOKE-REJECTED bad-syntax")
        return "REJECTED usage: REVOKE <token> <ip>"
    token, ip = parts[1], parts[2]
    if not token_ok(token):
        append(f"{_now()} {addr} REVOKE-DENIED")
        return "DENIED"
    if not roster.enabled():
        append(f"{_now()} {addr} REVOKE-ERROR no-database")
        return "ERROR no database"
    append(f"{_now()} {addr} REVOKE {ip}")
    try:
        await roster.remove(ip)
    except Exception as exc:  # noqa: BLE001 - see allow_verb
        append(f"{_now()} {addr} REVOKE-ERROR {ip} {exc!r}")
        return "ERROR roster write failed"
    append(f"{_now()} {addr} REVOKED-DEVICE {ip}")
    return f"REVOKED {ip}"


async def dispatch(msg: str, addr: str) -> str | None:
    if msg.startswith("MKDIR"):
        return mkdir_verb(msg, addr)
    if msg.startswith("ALLOW "):
        return await allow_verb(msg, addr)
    if msg.startswith("REVOKE "):
        return await revoke_verb(msg, addr)
    return None
