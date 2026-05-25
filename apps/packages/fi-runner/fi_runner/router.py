"""ModelRouter — pick the model per turn (e.g. tier routing).

The runner is model-agnostic: it takes a fixed ``model`` OR a ``ModelRouter`` that
chooses one per turn. A router with per-SESSION stickiness (same model for a whole
conversation) caches internally keyed off ``context`` (e.g. a session id) — the
runner stays dumb, the router owns the policy.

This is the seam a tiered router plugs into: insult's 3-tier
(Haiku/Sonnet/Opus) selection moves out of its hand-rolled agent loop and behind
this protocol when that loop migrates onto :meth:`fi_runner.Runner.run`.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ModelRouter(Protocol):
    """Chooses the model id for a turn. ``Runner`` calls this when set."""

    async def choose(
        self, *, user_message: str, default: str | None, context: dict[str, Any]
    ) -> str | None:
        """Return the model id to use for this turn, or ``None`` to keep
        ``default``. ``context`` carries per-turn side data (session id, user id,
        routing signals) — a sticky router reads/writes its own cache from it."""
        ...


__all__ = ["ModelRouter"]
