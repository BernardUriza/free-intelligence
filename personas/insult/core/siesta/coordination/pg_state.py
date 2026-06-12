"""Cross-process Siesta coordination via Postgres (v3.9.46, POST-DEPLOY-1).

Replaces `blob_metadata.py` — same public API, different backing store.
The consolidator job and the bot replica are different processes; they
share state through the `siesta_state` table (singleton row keyed by the
literal 'current').

Writers (consolidator):
- ``mark_started(total_users)`` at the top of the run.
- ``mark_progress(...)`` after each user/phase advance.
- ``mark_finished()`` at the very end (success or fail — bot must wake).

Reader (bot poller):
- ``read_snapshot()`` returns the current :class:`SiestaSnapshot`.

Why we switched off blob metadata:
The previous mechanism hijacked Azure blob metadata fields on the
`memory.db` blob. After the v3.8 migration to managed Postgres the
SQLite blob became legacy bytes nobody read — but we couldn't delete
the blob because its metadata was the only coordination channel.
That left a fantasma in the data plane. Moving to PG eliminates the
last reason to keep the blob around (POST-DEPLOY-1 fully unblocked).

Drop-in API parity with `blob_metadata` so callers don't change.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import asyncpg
import structlog

from personas.insult.core.siesta.state import AWAKE, SiestaPhase, SiestaSnapshot

log = structlog.get_logger()

_SINGLETON_KEY = "current"


async def _connect() -> asyncpg.Connection | None:
    """Open a one-shot connection. Returns None if PG is not configured.

    Siesta operations are infrequent (one read every 30s on the bot,
    a handful of writes per consolidator run), so a one-shot connection
    per call is fine and avoids needing to share the bot's pool with
    the consolidator process — they have different lifecycles.
    """
    url = os.environ.get("POSTGRES_URL")
    if not url:
        return None
    try:
        return await asyncpg.connect(url)
    except Exception:
        log.exception("siesta_pg_connect_failed")
        return None


async def _upsert(snapshot: SiestaSnapshot) -> bool:
    """Insert or update the singleton row. Returns True on success."""
    conn = await _connect()
    if conn is None:
        return False
    try:
        await conn.execute(
            """
            INSERT INTO siesta_state
              (singleton, phase, started_at, total_users, processed_users,
               current_user_id, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (singleton) DO UPDATE SET
              phase = EXCLUDED.phase,
              started_at = EXCLUDED.started_at,
              total_users = EXCLUDED.total_users,
              processed_users = EXCLUDED.processed_users,
              current_user_id = EXCLUDED.current_user_id,
              updated_at = NOW()
            """,
            _SINGLETON_KEY,
            snapshot.phase.value,
            snapshot.started_at,
            snapshot.total_users,
            snapshot.processed_users,
            snapshot.current_user_id,
        )
        return True
    except Exception:
        log.exception("siesta_pg_upsert_failed")
        return False
    finally:
        await conn.close()


async def mark_started(total_users: int, *, phase: SiestaPhase = SiestaPhase.LIGHT) -> bool:
    """Consolidator: announce the run is starting."""
    snapshot = SiestaSnapshot(
        phase=phase,
        started_at=datetime.now(UTC),
        total_users=total_users,
        processed_users=0,
    )
    return await _upsert(snapshot)


async def mark_progress(
    *,
    phase: SiestaPhase,
    started_at: datetime,
    total_users: int,
    processed_users: int,
    current_user_id: str | None = None,
) -> bool:
    """Consolidator: announce phase or per-user advance."""
    snapshot = SiestaSnapshot(
        phase=phase,
        started_at=started_at,
        total_users=total_users,
        processed_users=processed_users,
        current_user_id=current_user_id,
    )
    return await _upsert(snapshot)


async def mark_finished() -> bool:
    """Consolidator: clear the state so the bot wakes up.

    Always called in a ``finally`` so crashes don't trap the bot in a
    stuck siesta. Sets ``phase=awake`` and zeroes the counters.
    """
    return await _upsert(AWAKE)


async def read_snapshot() -> SiestaSnapshot:
    """Bot poller: fetch and parse the current state. Never raises.

    Returns AWAKE on any read failure, missing row, or unparsable phase.
    The bot must default to "not in siesta" when the truth is unknown —
    blocking the LLM on a missed read would be worse than a rare double-
    write race that the consolidator-side locks already guard against.
    """
    conn = await _connect()
    if conn is None:
        return AWAKE
    try:
        row = await conn.fetchrow(
            """
            SELECT phase, started_at, total_users, processed_users, current_user_id
            FROM siesta_state
            WHERE singleton = $1
            """,
            _SINGLETON_KEY,
        )
        if row is None:
            return AWAKE
        try:
            phase = SiestaPhase(row["phase"])
        except ValueError:
            log.warning("siesta_pg_invalid_phase", value=row["phase"])
            return AWAKE
        if phase == SiestaPhase.AWAKE:
            return AWAKE
        return SiestaSnapshot(
            phase=phase,
            started_at=row["started_at"],
            total_users=row["total_users"] or 0,
            processed_users=row["processed_users"] or 0,
            current_user_id=row["current_user_id"],
        )
    except Exception:
        log.exception("siesta_pg_read_failed")
        return AWAKE
    finally:
        await conn.close()
