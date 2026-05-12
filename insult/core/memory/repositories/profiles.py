"""User style profiles — EMA-tracked speech characteristics per user.

Migrated to asyncpg on 2026-05-12 PG migration. Profile JSON now lives
in a JSONB column instead of TEXT (Postgres-native), but we keep the
to_json / from_json round-trip because the UserStyleProfile dataclass
serializes itself and the JSONB column accepts the resulting string
without manual encoding."""

from __future__ import annotations

import time

import asyncpg
import structlog

from insult.core.memory.base import BaseRepository
from insult.core.style import UserStyleProfile

log = structlog.get_logger()


class ProfilesRepository(BaseRepository):
    """Owns the `user_profiles` table.

    The profile is serialized to JSON because the shape evolves (new
    metrics get added) and a schema migration per change would be painful
    for a field nobody queries on — we always load-by-user_id and update
    holistically. Confidence gates + adaptation logic live in `core/style`."""

    async def get_profile(self, user_id: str) -> UserStyleProfile:
        """Load the stored profile, or return a fresh default if none exists."""
        row = await self._fetchrow(
            "SELECT profile_json FROM user_profiles WHERE user_id = $1",
            user_id,
        )
        if row:
            raw = row["profile_json"]
            # JSONB returns dict-or-str depending on the codec path; normalize.
            payload = raw if isinstance(raw, str) else _serialize_jsonb(raw)
            return UserStyleProfile.from_json(payload)
        return UserStyleProfile()

    async def update_profile(self, user_id: str, message: str) -> UserStyleProfile:
        """Incorporate a new message into the user's style profile via EMA.

        Logs and swallows asyncpg errors so a DB hiccup doesn't crash the
        turn — the user still gets a response, the profile just stalls."""
        profile = await self.get_profile(user_id)
        profile.update(message)

        try:
            await self._execute(
                "INSERT INTO user_profiles (user_id, profile_json, updated_at) "
                "VALUES ($1, $2::jsonb, $3) "
                "ON CONFLICT(user_id) DO UPDATE SET "
                "profile_json=excluded.profile_json, updated_at=excluded.updated_at",
                user_id,
                profile.to_json(),
                time.time(),
            )
        except asyncpg.PostgresError as e:
            log.error("profile_update_failed", user_id=user_id, error=str(e))

        return profile


def _serialize_jsonb(value: object) -> str:
    """Render a JSONB value (dict/list returned by asyncpg's default codec)
    back to JSON text so `UserStyleProfile.from_json` (which expects a string)
    keeps working without caring whether the codec decoded or not."""
    import json

    return json.dumps(value)
