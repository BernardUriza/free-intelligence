"""The device whitelist (backlog #18) — deathless in the owner's Postgres."""

from .boot import start
from .state import allows, enabled, ready
from .writes import add, remove

__all__ = ["add", "allows", "enabled", "ready", "remove", "start"]
