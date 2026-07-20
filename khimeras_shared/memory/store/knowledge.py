"""Knowledge facade — user facts, agent self-knowledge, world scans, channel summaries."""

from __future__ import annotations

from khimeras_shared.memory.repositories import (
    AgentFactsRepository,
    ChannelSummariesRepository,
    FactsRepository,
    WorldScansRepository,
)


class KnowledgeFacade:
    _facts: FactsRepository
    _agent_facts: AgentFactsRepository
    _world_scans: WorldScansRepository
    _channels: ChannelSummariesRepository

    # -- Facts --

    async def get_facts(self, user_id: str) -> list[dict]:
        return await self._facts.get_facts(user_id)

    async def get_auto_facts(self, user_id: str) -> list[dict]:
        """Complete live auto-extracted set (not the semantic top-N). The
        fact-extraction backstop unions onto this so `save_facts`' snapshot
        replace can't hard-delete auto facts outside the prompt subset."""
        return await self._facts.get_auto_facts(user_id)

    async def get_facts_for_injection(self, user_id: str, auto_limit: int = 10) -> list[dict]:
        """Curated-first facts for the 'Other People' block, so a person's
        load-bearing curated facts (plans, origins, diagnoses) never get pushed
        out of the prompt by a burst of recent auto-extractions."""
        return await self._facts.get_facts_for_injection(user_id, auto_limit=auto_limit)

    async def get_all_facts(self) -> list[dict]:
        return await self._facts.get_all_facts()

    async def save_facts(self, user_id: str, facts: list[dict]) -> None:
        await self._facts.save_facts(user_id, facts)

    async def add_manual_fact(self, user_id: str, fact: str, category: str = "general") -> int:
        return await self._facts.add_manual_fact(user_id, fact, category)

    async def add_remember_fact(self, user_id: str, fact: str, category: str = "general") -> int:
        return await self._facts.add_remember_fact(user_id, fact, category)

    async def search_facts_semantic(self, user_id: str, query: str, limit: int = 10) -> list[dict]:
        return await self._facts.search_facts_semantic(user_id, query, limit)

    # -- Agent self-knowledge (reflection loop, slice 4) --

    async def get_agent_self_facts(self, agent_id: str, limit: int = 60) -> list[dict]:
        return await self._agent_facts.get_self_facts(agent_id, limit)

    async def add_agent_self_fact(self, agent_id: str, fact: str, category: str, provenance: str) -> int | None:
        return await self._agent_facts.add_self_fact(agent_id, fact, category, provenance)

    async def get_last_reflected_at(self, agent_id: str) -> float | None:
        return await self._agent_facts.get_last_reflected_at(agent_id)

    async def mark_reflected(self, agent_id: str, ts: float) -> None:
        await self._agent_facts.mark_reflected(agent_id, ts)

    # -- World scans --

    async def store_world_scan(
        self,
        topic: str,
        findings: str,
        commentary: str,
        *,
        source: str = "web",
        external_id: str | None = None,
    ) -> bool:
        return await self._world_scans.store_world_scan(
            topic, findings, commentary, source=source, external_id=external_id
        )

    async def get_recent_world_scans(self, limit: int = 5, source: str | None = None) -> list[dict]:
        return await self._world_scans.get_recent_world_scans(limit, source=source)

    async def has_external_id(self, source: str, external_id: str) -> bool:
        return await self._world_scans.has_external_id(source, external_id)

    # -- Channel summaries --

    async def upsert_channel_summary(
        self,
        guild_id: str,
        channel_id: str,
        channel_name: str,
        summary: str,
        message_count: int,
        last_message_ts: float,
        is_private: bool = False,
    ) -> None:
        await self._channels.upsert_channel_summary(
            guild_id,
            channel_id,
            channel_name,
            summary,
            message_count,
            last_message_ts,
            is_private,
        )

    async def get_channel_summaries(
        self,
        guild_id: str,
        exclude_channel_id: str | None = None,
        limit: int = 8,
    ) -> list[dict]:
        return await self._channels.get_channel_summaries(guild_id, exclude_channel_id, limit)
