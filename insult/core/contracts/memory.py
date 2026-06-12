"""Neutral structural contract for the memory store, as the debug server sees it.

The aiohttp debug server (`insult.core.debug_server`) only ever touches the
memory store through the `_MEMORY_KEY` app key and calls a fixed set of methods
off it. `DebugMemoryPort` captures exactly that surface so `debug_server.keys`
can type the app key without importing the concrete smart-side
`insult.core.memory.MemoryStore` (the host→smart boundary the demux destilado is
paying down).

Structural (`typing.Protocol`): `MemoryStore` satisfies it without inheriting —
same inversion the host-side `GuildConfigStore` Protocol uses. Stdlib-only, so
`contracts` stays a neutral leaf. The method signatures mirror
`insult/core/memory/store.py`; if the store's surface changes, update here too
(`test_contracts_extraction` asserts MemoryStore still satisfies this port).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DebugMemoryPort(Protocol):
    """The subset of the memory store the debug-server handlers depend on."""

    # --- auth (sync lane) ---
    async def resolve_sync_token(self, plaintext_token: str) -> str | None: ...

    # --- read paths (content / stats endpoints) ---
    async def get_recent(self, channel_id: str, limit: int = 20, user_id: str | None = None) -> list[dict]: ...
    async def get_stats(self, channel_id: str | None = None) -> dict: ...
    async def get_channels_overview(self, limit: int = 50) -> list[dict]: ...
    async def get_channel_activity_since(self, guild_id: str, since_ts: float) -> list[dict]: ...
    async def get_facts(self, user_id: str) -> list[dict]: ...
    async def list_disclosures(self, user_id: str, since_ts: float, limit: int = 50) -> list[dict]: ...
    async def get_arc(self, channel_id: str, user_id: str) -> dict | None: ...

    # --- write paths (arc / reminders / world-scan / serenityops) ---
    async def upsert_arc(
        self,
        channel_id: str,
        user_id: str,
        phase: str,
        phase_since: float,
        crisis_depth: int,
        recovery_signals: int,
        turns_in_phase: int,
    ) -> None: ...
    async def save_reminder(
        self,
        channel_id: str,
        guild_id: str | None,
        created_by: str,
        description: str,
        remind_at: float,
        mention_user_ids: str = "",
        recurring: str = "none",
        requires_ack: bool = False,
    ) -> int: ...
    async def get_pending_reminders(self, now: float) -> list[dict]: ...
    async def get_channel_reminders(self, channel_id: str) -> list[dict]: ...
    async def update_reminder_fields(
        self,
        reminder_id: int,
        *,
        new_remind_at: float | None = None,
        new_description: str | None = None,
    ) -> bool: ...
    async def delete_reminder(self, reminder_id: int) -> bool: ...
    async def store_world_scan(
        self,
        topic: str,
        findings: str,
        commentary: str,
        *,
        source: str = "web",
        external_id: str | None = None,
    ) -> bool: ...
    async def insert_serenityops_snapshot(
        self,
        user_id: str,
        curriculum: dict | None,
        opportunities: dict | None,
        client_version: str | None = None,
    ) -> int: ...


@runtime_checkable
class MemoryLifecyclePort(Protocol):
    """Lifecycle surface of the memory store visible to the host plumbing layer.

    app.py and bot.py need only open and close the connection pool — all
    smart-layer reads/writes go through cogs that receive the concrete store
    by injection.  Keeping this minimal is intentional: the governance goal
    is to sever the host→insult.core.memory import edge, not to model the
    full store interface here.
    """

    async def connect(self) -> None: ...
    async def close(self) -> None: ...
