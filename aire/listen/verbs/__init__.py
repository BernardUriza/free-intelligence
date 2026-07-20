"""Verb dispatch: a matched verb replies with an ACK; anything else is a report."""

from .allow import allow_verb
from .mkdir import mkdir_verb
from .revoke import revoke_verb

__all__ = ["dispatch"]


async def dispatch(msg: str, addr: str) -> str | None:
    if msg.startswith("MKDIR"):
        return mkdir_verb(msg, addr)
    if msg.startswith("ALLOW "):
        return await allow_verb(msg, addr)
    if msg.startswith("REVOKE "):
        return await revoke_verb(msg, addr)
    return None
