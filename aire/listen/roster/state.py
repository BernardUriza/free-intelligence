"""The roster cache: truth is Postgres (`aire_device`); this set is derived,
updated in lockstep with ALLOW/REVOKE and refreshed periodically. Reading it is
the second sanctioned exception in [[write-only-daemon]]."""

from ..config import DSN

IPS: set[str] = set()
READY = False


def enabled() -> bool:
    return bool(DSN)


def ready() -> bool:
    return READY


def allows(ip: str) -> bool:
    return ip in IPS
