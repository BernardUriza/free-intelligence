"""`MKDIR <token> <name>` → a fresh session casita; command-as-event, token redacted."""

import uuid
from datetime import datetime, timezone

from ..applog import _now, append
from ..config import NAME_RE, WORKSPACES
from .auth import token_ok


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
