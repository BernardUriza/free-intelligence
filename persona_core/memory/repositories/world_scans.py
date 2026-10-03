"""World scans — Insult's internal notes on what's happening out there.

Populated by a background task that summarizes news/topics into a findings
+ commentary pair. Read at turn-build time to give Insult cross-topic
awareness without requiring a web_search call on every message.

Migrated to asyncpg on 2026-05-12 PG migration. `INSERT OR IGNORE` →
`INSERT ... ON CONFLICT DO NOTHING` with `RETURNING id` so we can tell
inserted-from-deduped without parsing the command tag."""

from __future__ import annotations

import time

import asyncpg
import structlog

from persona_core.memory.base import BaseRepository

log = structlog.get_logger()


class WorldScansRepository(BaseRepository):
    """Owns the `world_scans` table."""

    async def store_world_scan(
        self,
        topic: str,
        findings: str,
        commentary: str,
        *,
        source: str = "web",
        external_id: str | None = None,
    ) -> bool:
        """Append a scan. Failures logged-not-raised — a dropped scan is recoverable.

        `source` discriminates ingestion origin (`web` for the existing
        web_search path; external-feed ingesters name their own).
        `external_id` enables dedupe via the partial UNIQUE index on
        (source, external_id) — `ON CONFLICT DO NOTHING` turns a duplicate
        into a no-op rather than a constraint error.

        Returns True if a row was inserted, False if it was a deduped no-op
        (same external post id seen twice). Web scans always insert."""
        try:
            # When the unique partial index matches an existing row, ON CONFLICT
            # DO NOTHING suppresses the insert and RETURNING yields zero rows;
            # asyncpg `fetchval` returns None in that case, which is our False signal.
            #
            # The index is partial (`WHERE external_id IS NOT NULL`), so we must
            # name an inferable conflict target explicitly — passing the index
            # predicate is the only form Postgres accepts here.
            if external_id is None:
                # Web scans bypass dedupe entirely — index does not cover NULLs.
                row_id = await self._fetchval(
                    "INSERT INTO world_scans (topic, findings, commentary, timestamp, source, external_id) "
                    "VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
                    topic,
                    findings,
                    commentary,
                    time.time(),
                    source,
                    external_id,
                )
            else:
                row_id = await self._fetchval(
                    "INSERT INTO world_scans (topic, findings, commentary, timestamp, source, external_id) "
                    "VALUES ($1, $2, $3, $4, $5, $6) "
                    "ON CONFLICT (source, external_id) WHERE external_id IS NOT NULL DO NOTHING "
                    "RETURNING id",
                    topic,
                    findings,
                    commentary,
                    time.time(),
                    source,
                    external_id,
                )
            inserted = row_id is not None
            if inserted:
                log.info("world_scan_stored", topic=topic[:80], source=source, external_id=external_id)
            else:
                log.debug("world_scan_dedup_skipped", source=source, external_id=external_id)
            return inserted
        except asyncpg.PostgresError as e:
            log.error("world_scan_store_failed", error=str(e), source=source)
            return False

    async def get_recent_world_scans(self, limit: int = 5, source: str | None = None) -> list[dict]:
        """Most recent scans for prompt injection.

        When `source` is None, returns scans from any source (legacy behavior).
        Pass `source='web'` to keep the original-only feed, or a specific
        source name to read only that ingestion stream."""
        if source is None:
            rows = await self._fetch(
                "SELECT topic, findings, commentary, timestamp, source, external_id "
                "FROM world_scans ORDER BY timestamp DESC LIMIT $1",
                limit,
            )
        else:
            rows = await self._fetch(
                "SELECT topic, findings, commentary, timestamp, source, external_id "
                "FROM world_scans WHERE source = $1 ORDER BY timestamp DESC LIMIT $2",
                source,
                limit,
            )
        return [
            {
                "topic": r["topic"],
                "findings": r["findings"],
                "commentary": r["commentary"],
                "timestamp": r["timestamp"],
                "source": r["source"],
                "external_id": r["external_id"],
            }
            for r in rows
        ]

    async def has_external_id(self, source: str, external_id: str) -> bool:
        """Quick existence check so an external-feed ingester can skip posts
        already curated. Cheaper than the full INSERT ... ON CONFLICT round
        when the caller wants to short-circuit BEFORE running the LLM."""
        val = await self._fetchval(
            "SELECT 1 FROM world_scans WHERE source = $1 AND external_id = $2 LIMIT 1",
            source,
            external_id,
        )
        return val is not None
