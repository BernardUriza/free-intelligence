"""Admission at accept(): rate token, then the whitelist gate (backlog #18).
FAIL CLOSED when enforcing: an unloaded roster denies — a security control that
self-disables on a DB blip is worse than none. The DENIED-DEVICE line cures
Carlos's failure #1: you SEE the forgotten device knocking."""

from .. import roster
from ..applog import _now, append
from ..config import WHITELIST_ENFORCE
from .bucket import BUCKET


def admit(ip: str, addr: str, exempt: bool) -> bool:
    if exempt:
        return True
    if not BUCKET.allow(ip):
        return False
    if WHITELIST_ENFORCE and not (roster.enabled() and roster.ready() and roster.allows(ip)):
        append(f"{_now()} {addr} DENIED-DEVICE")
        return False
    return True
