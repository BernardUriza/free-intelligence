"""Source registry — string→Source lookup.

The lanes in bot.py never instantiate concrete sources directly. They
ask the registry for the Source they want, the registry returns the
configured instance (or raises if it is not registered / not configured).
This isolates the question of *which* sources are enabled to one place
— bot.py wiring at startup — and keeps lane code platform-agnostic.

Concrete sources call `register_source` on construction. The registry
is a process-wide singleton dict; tests can clear it via the underscore
private API if they need isolation.
"""

from __future__ import annotations

from personas.insult.core.sources.base import Source

_REGISTRY: dict[str, Source] = {}


def register_source(source: Source) -> None:
    """Add a Source to the registry under its `name`. Idempotent: registering
    the same name twice replaces the prior instance (last writer wins) so
    test setup / teardown can rebind without leaking."""
    _REGISTRY[source.name] = source


def get_source(name: str) -> Source:
    """Return the registered Source for `name`. Raises KeyError if not
    registered — callers should treat that as 'platform not configured for
    this deployment' rather than crashing the bot."""
    try:
        return _REGISTRY[name]
    except KeyError as e:
        raise KeyError(f"No Source registered under name {name!r}. Registered: {list(_REGISTRY)}") from e


def list_sources() -> list[str]:
    """Names of currently registered sources. Used by debug endpoints."""
    return sorted(_REGISTRY)


def _clear() -> None:
    """Test-only: empty the registry. Not exported via __init__."""
    _REGISTRY.clear()
