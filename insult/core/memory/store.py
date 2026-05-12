"""MemoryStore — thin facade over the repositories.

The facade preserves the legacy flat API (`memory.store(...)`,
`memory.get_facts(...)`, etc.) so ~25 callsites across chat.py, bot.py,
utility cog, debug_server, proactive, and the facts/arc flows keep
working with zero changes. Each method is a one-line delegation to the
repository that owns the relevant table.

Why a facade rather than "import the repos directly everywhere":
- Backwards compatibility: one class = one injection point in the DI
  container (`app.py::Container.memory`). Rewiring every callsite to take
  specific repos would be a sweeping change for no real benefit.
- Locality of schema evolution: if tomorrow we need to route messages to
  a different backend than facts, only the facade changes — callers
  keep calling `memory.store(...)`.
"""

from __future__ import annotations

from insult.core.memory.connection import ConnectionManager
from insult.core.memory.context import build_context, format_relative_time
from insult.core.memory.repositories import (
    ChannelSummariesRepository,
    DisclosureRepository,
    FactsRepository,
    GuildConfigRepository,
    MessagesRepository,
    ProfilesRepository,
    RelationalStateRepository,
    RemindersRepository,
    SerenityOpsRepository,
    WorldScansRepository,
)
from insult.core.style import UserStyleProfile


class MemoryStore:
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
        self._relational = RelationalStateRepository(self._manager)
        self._channels = ChannelSummariesRepository(self._manager)
        self._world_scans = WorldScansRepository(self._manager)
        self._disclosure = DisclosureRepository(self._manager)
        self._guild_config = GuildConfigRepository(self._manager)
        self._serenityops = SerenityOpsRepository(self._manager)

    # -- Lifecycle --

    async def connect(self) -> None:
        await self._manager.connect()

    async def close(self) -> None:
        await self._manager.close()

    @property
    def _vectors_available(self) -> bool:
        return self._manager.vectors_available

    # -- Messages --

    async def store(
        self,
        channel_id: str,
        user_id: str,
        user_name: str,
        role: str,
        content: str,
        for_user_id: str | None = None,
        guild_id: str | None = None,
        channel_name: str | None = None,
        model_used: str | None = None,
    ) -> None:
        await self._messages.store(
            channel_id,
            user_id,
            user_name,
            role,
            content,
            for_user_id=for_user_id,
            guild_id=guild_id,
            channel_name=channel_name,
            model_used=model_used,
        )

    async def get_recent(self, channel_id: str, limit: int = 20, user_id: str | None = None) -> list[dict]:
        return await self._messages.get_recent(channel_id, limit, user_id)

    async def search(self, channel_id: str, query: str, limit: int = 5, user_id: str | None = None) -> list[dict]:
        return await self._messages.search(channel_id, query, limit, user_id)

    async def get_stats(self, channel_id: str | None = None) -> dict:
        return await self._messages.get_stats(channel_id)

    async def delete_before(self, cutoff: float) -> int:
        return await self._messages.delete_before(cutoff)

    async def count_before(self, cutoff: float) -> int:
        return await self._messages.count_before(cutoff)

    async def get_latest_username_per_user(self) -> dict[str, str]:
        return await self._messages.get_latest_username_per_user()

    async def get_all_user_messages(self, limit_per_user: int = 30) -> dict[str, dict]:
        return await self._messages.get_all_user_messages(limit_per_user)

    async def get_recent_for_summary(self, channel_id: str, limit: int = 50) -> list[dict]:
        return await self._messages.get_recent_for_summary(channel_id, limit)

    async def get_channel_participants(self, channel_id: str, limit: int = 10) -> list[dict]:
        return await self._messages.get_channel_participants(channel_id, limit)

    async def get_channel_activity_since(self, guild_id: str, since_ts: float) -> list[dict]:
        return await self._messages.get_channel_activity_since(guild_id, since_ts)

    async def get_channels_overview(self, limit: int = 50) -> list[dict]:
        return await self._messages.get_channels_overview(limit)

    # -- Profiles --

    async def get_profile(self, user_id: str) -> UserStyleProfile:
        return await self._profiles.get_profile(user_id)

    async def update_profile(self, user_id: str, message: str) -> UserStyleProfile:
        return await self._profiles.update_profile(user_id, message)

    # -- Facts --

    async def get_facts(self, user_id: str) -> list[dict]:
        return await self._facts.get_facts(user_id)

    async def get_all_facts(self) -> list[dict]:
        return await self._facts.get_all_facts()

    async def save_facts(self, user_id: str, facts: list[dict]) -> None:
        await self._facts.save_facts(user_id, facts)

    async def add_manual_fact(self, user_id: str, fact: str, category: str = "general") -> int:
        return await self._facts.add_manual_fact(user_id, fact, category)

    async def search_facts_semantic(self, user_id: str, query: str, limit: int = 10) -> list[dict]:
        return await self._facts.search_facts_semantic(user_id, query, limit)

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

    # -- Reminders --

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
    ) -> int:
        return await self._reminders.save_reminder(
            channel_id,
            guild_id,
            created_by,
            description,
            remind_at,
            mention_user_ids,
            recurring,
            requires_ack=requires_ack,
        )

    async def get_pending_reminders(self, now: float) -> list[dict]:
        return await self._reminders.get_pending_reminders(now)

    async def set_ack_metadata(self, reminder_id: int, ack_msg_id: int, delivered_at: float) -> None:
        await self._reminders.set_ack_metadata(reminder_id, ack_msg_id, delivered_at)

    async def mark_ack_received(self, ack_msg_id: int) -> bool:
        return await self._reminders.mark_ack_received(ack_msg_id)

    async def get_ack_overdue(self, now: float, timeout_seconds: float, max_retries: int) -> list[dict]:
        return await self._reminders.get_ack_overdue(now, timeout_seconds, max_retries)

    async def increment_ack_retry(self, reminder_id: int) -> None:
        await self._reminders.increment_ack_retry(reminder_id)

    async def mark_reminder_delivered(self, reminder_id: int) -> None:
        await self._reminders.mark_reminder_delivered(reminder_id)

    async def update_reminder_time(self, reminder_id: int, new_remind_at: float) -> None:
        await self._reminders.update_reminder_time(reminder_id, new_remind_at)

    async def update_reminder_fields(
        self,
        reminder_id: int,
        *,
        new_remind_at: float | None = None,
        new_description: str | None = None,
    ) -> bool:
        return await self._reminders.update_reminder_fields(
            reminder_id,
            new_remind_at=new_remind_at,
            new_description=new_description,
        )

    async def get_channel_reminders(self, channel_id: str) -> list[dict]:
        return await self._reminders.get_channel_reminders(channel_id)

    async def delete_reminder(self, reminder_id: int) -> bool:
        return await self._reminders.delete_reminder(reminder_id)

    async def set_snooze_msg_id(self, reminder_id: int, msg_id: int) -> None:
        await self._reminders.set_snooze_msg_id(reminder_id, msg_id)

    async def get_reminder_for_snooze(self, msg_id: int) -> dict | None:
        return await self._reminders.get_reminder_for_snooze(msg_id)

    async def clear_snooze_msg_id(self, msg_id: int) -> None:
        await self._reminders.clear_snooze_msg_id(msg_id)

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

    # -- Context building (pure functions delegated for backwards compat) --

    @staticmethod
    def _format_relative_time(timestamp: float) -> str:
        return format_relative_time(timestamp)

    def build_context(self, recent: list[dict], relevant: list[dict] | None = None) -> list[dict]:
        return build_context(recent, relevant)
