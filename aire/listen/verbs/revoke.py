"""`REVOKE <token> <ip>` → remove a device from the whitelist."""

from .. import roster
from ..applog import _now, append
from .auth import token_ok


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
        return "ERROR no database"
    await roster.remove(ip)
    append(f"{_now()} {addr} REVOKED-DEVICE {ip}")
    return f"REVOKED {ip}"
