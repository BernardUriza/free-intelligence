"""Governance facade — disclosure, relational state, guild config, SerenityOps sync."""

from __future__ import annotations

from persona_core.memory.repositories import (
    DisclosureRepository,
    GuildConfigRepository,
    RelationalStateRepository,
    SerenityOpsRepository,
)


class GovernanceFacade:
    _disclosure: DisclosureRepository
    _relational: RelationalStateRepository
    _guild_config: GuildConfigRepository
    _serenityops: SerenityOpsRepository

    # -- Disclosure --

    async def store_disclosure(
        self,
        channel_id: str,
        user_id: str,
        category: str,
        severity: int,
        signals: str,
        excerpt: str,
    ) -> None:
        await self._disclosure.store_disclosure(channel_id, user_id, category, severity, signals, excerpt)

    async def get_recent_max_severity(self, user_id: str, since_ts: float) -> int:
        return await self._disclosure.get_recent_max_severity(user_id, since_ts)

    async def list_disclosures(self, user_id: str, since_ts: float, limit: int = 50) -> list[dict]:
        return await self._disclosure.list_disclosures(user_id, since_ts, limit)

    # -- Relational state (arcs + stance + contradictions) --

    async def get_arc(self, channel_id: str, user_id: str) -> dict | None:
        return await self._relational.get_arc(channel_id, user_id)

    async def upsert_arc(
        self,
        channel_id: str,
        user_id: str,
        phase: str,
        phase_since: float,
        crisis_depth: int,
        recovery_signals: int,
        turns_in_phase: int,
    ) -> None:
        await self._relational.upsert_arc(
            channel_id,
            user_id,
            phase,
            phase_since,
            crisis_depth,
            recovery_signals,
            turns_in_phase,
        )

    async def store_stance(
        self,
        channel_id: str,
        user_id: str,
        topic: str,
        position: str,
        confidence: float,
    ) -> None:
        await self._relational.store_stance(channel_id, user_id, topic, position, confidence)

    async def get_stances(self, channel_id: str, user_id: str, limit: int = 5) -> list[dict]:
        return await self._relational.get_stances(channel_id, user_id, limit)

    async def store_contradiction(self, user_id: str, prior: str, contradicting: str, topic: str) -> None:
        await self._relational.store_contradiction(user_id, prior, contradicting, topic)

    # -- Guild config --

    async def get_guild_config(self, guild_id: str) -> dict | None:
        return await self._guild_config.get_guild_config(guild_id)

    async def save_guild_config(
        self,
        guild_id: str,
        category_id: str,
        facts_channel_id: str,
        reminders_channel_id: str,
    ) -> None:
        await self._guild_config.save_guild_config(guild_id, category_id, facts_channel_id, reminders_channel_id)

    # -- SerenityOps sync (v3.8.0) --

    async def insert_serenityops_snapshot(
        self,
        user_id: str,
        curriculum: dict | None,
        opportunities: dict | None,
        client_version: str | None = None,
    ) -> int:
        return await self._serenityops.insert_snapshot(user_id, curriculum, opportunities, client_version)

    async def get_latest_serenityops_snapshot(self, user_id: str) -> dict | None:
        return await self._serenityops.get_latest_snapshot(user_id)

    async def create_sync_token(self, user_id: str, plaintext_token: str) -> int:
        return await self._serenityops.create_token(user_id, plaintext_token)

    async def revoke_sync_tokens(self, user_id: str) -> int:
        return await self._serenityops.revoke_all_for_user(user_id)

    async def resolve_sync_token(self, plaintext_token: str) -> str | None:
        return await self._serenityops.resolve_token(plaintext_token)
