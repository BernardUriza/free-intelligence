"""Boot/liveness state for the persona gateway.

The gateway hosts N Discord bots in one process, so it cannot reuse Insult's
single-bot ``core.health_state.HealthState`` singleton — "is the bot ready" has
no single answer here. What ``/health`` must report instead is per-persona:
which ones finished ``on_ready``, which ones died, and whether the shared
Postgres connection came up.

The load-bearing property is that ``/health`` never claims to be serving when
no persona has logged in. A gateway that answers ``{"status": "ok"}`` while
every bot is mute is the same boot-zombie that reported ``is_ready: true`` for
14 minutes on 2026-06-13 — a proxy that lies.

Liveness ("the process answers") and serving ("a persona can actually reply")
are different questions and get different fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GatewayBootState:
    """Mutable boot signals shared between ``_main`` and the HTTP app."""

    db_connected: bool = False
    personas_down: set[str] = field(default_factory=set)

    def mark_db_connected(self) -> None:
        self.db_connected = True

    def mark_persona_down(self, persona_id: str) -> None:
        self.personas_down.add(persona_id)

    def is_down(self, persona_id: str) -> bool:
        return persona_id in self.personas_down
