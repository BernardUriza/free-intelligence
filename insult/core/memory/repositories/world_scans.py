"""World scans — Insult's internal notes on what's happening out there.

Populated by a background task that summarizes news/topics into a findings
+ commentary pair. Read at turn-build time to give Insult cross-topic
awareness without requiring a web_search call on every message."""

from __future__ import annotations

import time

import aiosqlite
import structlog

from insult.core.memory.base import BaseRepository

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
        web_search path, `moltbook` and friends for the carretera).
        `external_id` enables dedupe via the partial UNIQUE index on
        (source, external_id) — INSERT OR IGNORE turns a duplicate into
        a no-op rather than a constraint error.

        Returns True if a row was inserted, False if it was a deduped no-op
        (e.g. same Moltbook post id seen twice). Web scans always insert."""
        db = await self._conn()
        try:
            cursor = await db.execute(
                "INSERT OR IGNORE INTO world_scans "
                "(topic, findings, commentary, timestamp, source, external_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (topic, findings, commentary, time.time(), source, external_id),
            )
            await db.commit()
            inserted = cursor.rowcount > 0
            if inserted:
                log.info("world_scan_stored", topic=topic[:80], source=source, external_id=external_id)
            else:
                log.debug("world_scan_dedup_skipped", source=source, external_id=external_id)
            return inserted
        except aiosqlite.Error as e:
            log.error("world_scan_store_failed", error=str(e), source=source)
            return False

    async def get_recent_world_scans(self, limit: int = 5, source: str | None = None) -> list[dict]:
        """Most recent scans for prompt injection.

        When `source` is None, returns scans from any source (legacy behavior).
        Pass `source='web'` to keep the original-only feed, or e.g.
        `source='moltbook'` to read only the Moltbook digest stream."""
        db = await self._conn()
        if source is None:
            cursor = await db.execute(
                "SELECT topic, findings, commentary, timestamp, source, external_id "
                "FROM world_scans ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
        else:
            cursor = await db.execute(
                "SELECT topic, findings, commentary, timestamp, source, external_id "
                "FROM world_scans WHERE source = ? ORDER BY timestamp DESC LIMIT ?",
                (source, limit),
            )
        rows = await cursor.fetchall()
        return [
            {
                "topic": r[0],
                "findings": r[1],
                "commentary": r[2],
                "timestamp": r[3],
                "source": r[4],
                "external_id": r[5],
            }
            for r in rows
        ]

    async def has_external_id(self, source: str, external_id: str) -> bool:
        """Quick existence check used by the inbound digest fetcher to skip
        posts already curated. Cheaper than the full INSERT OR IGNORE round
        when the caller wants to short-circuit BEFORE running the LLM."""
        db = await self._conn()
        cursor = await db.execute(
            "SELECT 1 FROM world_scans WHERE source = ? AND external_id = ? LIMIT 1",
            (source, external_id),
        )
        row = await cursor.fetchone()
        return row is not None
