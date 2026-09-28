"""MemoryStore — thin facade over the repositories.

The facade preserves the legacy flat API (`memory.store(...)`,
`memory.get_facts(...)`, etc.) so ~25 callsites across the gateway, the
workers, and the facts/arc flows keep working with zero changes. Each
method is a one-line delegation to the repository that owns the relevant
table.

Why a facade rather than "import the repos directly everywhere":
- Backwards compatibility: one class = one injection point. Rewiring
  every callsite to take specific repos would be a sweeping change for
  no real benefit.
- Locality of schema evolution: if tomorrow we need to route messages to
  a different backend than facts, only the facade changes — callers
  keep calling `memory.store(...)`.

Split by responsibility (2026-07-20): `conversation` (messages, profiles,
context), `knowledge` (facts, agent self-facts, world scans, channel
summaries), `scheduling` (reminders, research jobs, agendas), `governance`
(disclosure, relational state, guild config, SerenityOps). `MemoryStore`
composes the four facade mixins over the shared repositories.
"""

from __future__ import annotations

from persona_core.memory.connection import ConnectionManager
from persona_core.memory.repositories import (
    AgendasRepository,
    AgentFactsRepository,
    ChannelSummariesRepository,
    DisclosureRepository,
    FactsRepository,
    GuildConfigRepository,
    InviteTurnsRepository,
    MessagesRepository,
    ProfilesRepository,
    RelationalStateRepository,
    RemindersRepository,
    ResearchJobsRepository,
    SerenityOpsRepository,
    WorldScansRepository,
)
from persona_core.memory.store.conversation import ConversationFacade
from persona_core.memory.store.governance import GovernanceFacade
from persona_core.memory.store.knowledge import KnowledgeFacade
from persona_core.memory.store.scheduling import SchedulingFacade
from persona_core.memory.store.turns import InviteTurnsFacade


class MemoryStore(ConversationFacade, KnowledgeFacade, SchedulingFacade, GovernanceFacade, InviteTurnsFacade):
    """Facade over the domain repositories. Preserves the legacy API.

    Post-PG migration: takes a Postgres DSN. The container is stateless;
    persistence lives in Azure Database for PostgreSQL Flexible Server.
    Deploys NO LONGER mutate the DB.
    """

    def __init__(self, postgres_url: str):
        self.postgres_url = postgres_url
        self._manager = ConnectionManager(postgres_url)

        # Compose repositories. Each takes the shared manager so they all
        # read/write through the same asyncpg pool.
        self._messages = MessagesRepository(self._manager)
        self._profiles = ProfilesRepository(self._manager)
        self._facts = FactsRepository(self._manager)
        self._reminders = RemindersRepository(self._manager)
        self._research_jobs = ResearchJobsRepository(self._manager)
        self._agendas = AgendasRepository(self._manager)
        self._agent_facts = AgentFactsRepository(self._manager)
        self._relational = RelationalStateRepository(self._manager)
        self._channels = ChannelSummariesRepository(self._manager)
        self._world_scans = WorldScansRepository(self._manager)
        self._disclosure = DisclosureRepository(self._manager)
        self._guild_config = GuildConfigRepository(self._manager)
        self._serenityops = SerenityOpsRepository(self._manager)
        self._invite_turns = InviteTurnsRepository(self._manager)

    # -- Lifecycle --

    async def connect(self) -> None:
        await self._manager.connect()

    async def close(self) -> None:
        await self._manager.close()

    @property
    def _vectors_available(self) -> bool:
        return self._manager.vectors_available


__all__ = ["MemoryStore"]
