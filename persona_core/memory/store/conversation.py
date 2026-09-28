"""Conversation facade — messages, style profiles, context building."""

from __future__ import annotations

from persona_core.memory.context import SELF_BOT_USER_NAME, build_context, format_relative_time
from persona_core.memory.repositories import MessagesRepository, ProfilesRepository
from persona_core.style import UserStyleProfile


class ConversationFacade:
    _messages: MessagesRepository
    _profiles: ProfilesRepository

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
        discord_message_id: str | None = None,
        reactions: list[str] | None = None,
        origin: str | None = None,
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
            discord_message_id=discord_message_id,
            reactions=reactions,
            origin=origin,
        )

    async def append_to_message(self, discord_message_id: str, suffix: str) -> bool:
        return await self._messages.append_content_by_discord_id(discord_message_id, suffix)

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

    async def get_latest_username(self, user_id: str) -> str | None:
        return await self._messages.get_latest_username(user_id)

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

    async def recent_assistant_turns(self, user_name: str, limit: int = 40) -> list[dict]:
        return await self._messages.recent_assistant_turns(user_name, limit)

    # -- Profiles --

    async def get_profile(self, user_id: str) -> UserStyleProfile:
        return await self._profiles.get_profile(user_id)

    async def update_profile(self, user_id: str, message: str) -> UserStyleProfile:
        return await self._profiles.update_profile(user_id, message)

    # -- Context building (pure functions delegated for backwards compat) --

    @staticmethod
    def _format_relative_time(timestamp: float) -> str:
        return format_relative_time(timestamp)

    def build_context(self, recent: list[dict], *, self_name: str = SELF_BOT_USER_NAME) -> list[dict]:
        return build_context(recent, self_name=self_name)
