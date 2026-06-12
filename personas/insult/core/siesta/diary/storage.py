"""Repository for ``dream_diary`` rows.

Thin SQL wrappers — no business logic, no LLM calls. The schema lives
in :mod:`insult.core.memory.connection`. Post-PG migration this module
talks to the shared asyncpg pool via the memory store's manager so it
shares the same connection lifecycle as every other table.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from personas.insult.core.memory import MemoryStore

log = structlog.get_logger()

VALID_STATUS = ("ok", "partial", "failed")


@dataclass(frozen=True)
class DreamEntry:
    """One row in ``dream_diary``."""

    id: int
    run_ts: float
    duration_ms: int
    users_total: int
    users_processed: int
    facts_in_total: int
    facts_out_total: int
    deletes_total: int
    updates_total: int
    status: str
    content: str
    error: str | None


def _record_to_entry(row) -> DreamEntry:
    """Build a DreamEntry from an asyncpg.Record. Named access throughout
    so the projection in SELECT can change order without breaking unpacking."""
    return DreamEntry(
        id=row["id"],
        run_ts=row["run_ts"],
        duration_ms=row["duration_ms"],
        users_total=row["users_total"],
        users_processed=row["users_processed"],
        facts_in_total=row["facts_in_total"],
        facts_out_total=row["facts_out_total"],
        deletes_total=row["deletes_total"],
        updates_total=row["updates_total"],
        status=row["status"],
        content=row["content"],
        error=row["error"],
    )


def _pool(memory: MemoryStore):
    """Return the manager's pool, or None if the store isn't connected.

    Lives at module level so the three callsites below stay one-liner
    short-circuits. Callers that hit a None pool log + return empty/None
    — the diary is a non-critical observability surface, not a data plane."""
    pool = memory._manager.pool
    return pool


async def insert_entry(
    memory: MemoryStore,
    *,
    duration_ms: int,
    users_total: int,
    users_processed: int,
    facts_in_total: int,
    facts_out_total: int,
    deletes_total: int,
    updates_total: int,
    status: str,
    content: str,
    error: str | None = None,
    run_ts: float | None = None,
) -> int | None:
    """Persist one diary row. Returns the new id, or None on failure."""
    if status not in VALID_STATUS:
        raise ValueError(f"invalid status {status!r}; must be one of {VALID_STATUS}")
    pool = _pool(memory)
    if pool is None:
        log.warning("dream_diary_insert_skipped_no_db")
        return None
    new_id = await pool.fetchval(
        "INSERT INTO dream_diary "
        "(run_ts, duration_ms, users_total, users_processed, "
        " facts_in_total, facts_out_total, deletes_total, updates_total, "
        " status, content, error) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11) RETURNING id",
        run_ts if run_ts is not None else time.time(),
        duration_ms,
        users_total,
        users_processed,
        facts_in_total,
        facts_out_total,
        deletes_total,
        updates_total,
        status,
        content,
        error,
    )
    return int(new_id) if new_id is not None else None


async def latest_entry(memory: MemoryStore) -> DreamEntry | None:
    """Most recent diary row, or None if the table is empty."""
    pool = _pool(memory)
    if pool is None:
        return None
    row = await pool.fetchrow(
        "SELECT id, run_ts, duration_ms, users_total, users_processed, "
        "facts_in_total, facts_out_total, deletes_total, updates_total, "
        "status, content, error "
        "FROM dream_diary ORDER BY run_ts DESC LIMIT 1"
    )
    return _record_to_entry(row) if row else None


async def recent_entries(memory: MemoryStore, limit: int = 5) -> list[DreamEntry]:
    """Most recent ``limit`` entries, newest first."""
    pool = _pool(memory)
    if pool is None:
        return []
    rows = await pool.fetch(
        "SELECT id, run_ts, duration_ms, users_total, users_processed, "
        "facts_in_total, facts_out_total, deletes_total, updates_total, "
        "status, content, error "
        "FROM dream_diary ORDER BY run_ts DESC LIMIT $1",
        limit,
    )
    return [_record_to_entry(r) for r in rows]
