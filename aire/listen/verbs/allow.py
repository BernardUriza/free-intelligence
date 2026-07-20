"""`ALLOW <token> <ip> [note]` → add a device to the deathless whitelist. The
roster's changes are events like everything else (`ALLOWED-DEVICE`)."""

from .. import roster
from ..applog import _now, append
from .auth import token_ok, valid_ip


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
        return "ERROR no database (whitelist needs AIRE_DATABASE_URL)"
    await roster.add(ip, parts[3] if len(parts) > 3 else "")
    append(f"{_now()} {addr} ALLOWED-DEVICE {ip}")
    return f"ALLOWED {ip}"
