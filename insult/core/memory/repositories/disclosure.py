"""Disclosure log — severity-tagged record of user self-disclosures.

Populated by the `core/disclosure` scanner whenever a user reveals
personal or sensitive information (mental health, relationships, etc.).
Used for telemetry and to trigger downstream escalations; the persona
does NOT cite these entries directly.

Migrated to asyncpg on 2026-05-12 PG migration.
"""

from __future__ import annotations

import time

import asyncpg
import structlog

from insult.core.memory.base import BaseRepository

log = structlog.get_logger()


class DisclosureRepository(BaseRepository):
    """Owns the `disclosure_log` table."""

    async def store_disclosure(
        self,
        channel_id: str,
        user_id: str,
        category: str,
        severity: int,
        signals: str,
        excerpt: str,
    ) -> None:
        try:
            await self._execute(
                "INSERT INTO disclosure_log (channel_id, user_id, category, severity, signals, "
                "message_excerpt, timestamp) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                channel_id,
                user_id,
                category,
                severity,
                signals,
                excerpt[:200],
                time.time(),
            )
        except asyncpg.PostgresError as e:
            log.error("disclosure_store_failed", error=str(e))

    async def list_disclosures(self, user_id: str, since_ts: float, limit: int = 50) -> list[dict]:
        """Return disclosure rows for a user since a timestamp, most recent first.

        Lives here (rather than in the debug server) so the debug endpoint
        doesn't reach into private `_conn()` internals — the repository
        owns the SQL, callers consume typed dicts.
        """
        rows = await self._fetch(
            "SELECT timestamp, channel_id, category, severity, message_excerpt "
            "FROM disclosure_log WHERE user_id = $1 AND timestamp >= $2 "
            "ORDER BY timestamp DESC LIMIT $3",
            user_id,
            since_ts,
            limit,
        )
        return [
            {
                "timestamp": r["timestamp"],
                "channel_id": r["channel_id"],
                "category": r["category"],
                "severity": r["severity"],
                "excerpt": r["message_excerpt"],
            }
            for r in rows
        ]

    async def get_recent_max_severity(self, user_id: str, since_ts: float) -> int:
        """Return the maximum severity logged for a user since a timestamp.

        Used by the OUTBOUND gate: if a user disclosed something at severity
        ≥ 3 in the recent past, posting external content that mentions or
        adjacents that disclosure is unsafe — bail out of the entire posting
        flow regardless of how the draft is redacted.

        Returns 0 if there are no rows since the cutoff."""
        val = await self._fetchval(
            "SELECT MAX(severity) FROM disclosure_log WHERE user_id = $1 AND timestamp >= $2",
            user_id,
            since_ts,
        )
        return int(val) if val is not None else 0
