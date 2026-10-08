"""La fila del boleto del runner — `persona_core.tickets.TicketLedger` sobre Postgres.

The runner OWNS this table (same contract as `aire_topics`): it is the only
reader and writer, its DDL rides here and is applied once per process on first
use, and every method returns ``None`` when Postgres is unreachable so the
registry degrades to RAM instead of killing a turn.

Qué guarda: el request del turno (sin adjuntos — base64 de varios MB que no
vale persistir; un job con adjuntos es no-reanudable), quién lo corre
(`claimed_by`, uuid por proceso), su latido, cuándo cruzó a AIRE
(`aire_sent_at`: al reanudar, la historia ya no se pliega) y su resultado.
Todo el reloj es el de la base (`now()`): dos réplicas no pueden discrepar por
skew sobre si un latido ya venció.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from persona_core.tickets import LedgerRow

log = structlog.get_logger()

_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS turn_jobs (
    job_id        TEXT PRIMARY KEY,
    label         TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('queued', 'running', 'done', 'failed', 'abandoned')),
    attempts      INTEGER NOT NULL DEFAULT 1,
    claimed_by    TEXT,
    request       JSONB NOT NULL,
    response      JSONB,
    error         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    claimed_at    TIMESTAMPTZ,
    heartbeat_at  TIMESTAMPTZ,
    aire_sent_at  TIMESTAMPTZ,
    finished_at   TIMESTAMPTZ,
    deadline_at   TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_turn_jobs_open
    ON turn_jobs (status, heartbeat_at) WHERE status IN ('queued', 'running');
"""

_OPEN_SQL = """
INSERT INTO turn_jobs (job_id, label, status, attempts, claimed_by, request, claimed_at, heartbeat_at, deadline_at)
VALUES ($1, $2, 'running', 1, $3, $4::jsonb, now(), now(), now() + ($5::double precision * interval '1 second'))
ON CONFLICT (job_id) DO NOTHING
RETURNING job_id
"""

_GET_SQL = """
SELECT job_id, label, status, attempts, claimed_by, request, response, error, aire_sent_at,
       (heartbeat_at IS NULL OR heartbeat_at < now() - ($2::double precision * interval '1 second')) AS stale
FROM turn_jobs WHERE job_id = $1
"""

# Compare-and-swap: la fila la gana exactamente un proceso. Un dueño vivo
# (latido fresco), un id ya nuestro, los intentos agotados o un deadline vencido
# devuelven cero filas.
_CLAIM_SQL = """
UPDATE turn_jobs
   SET claimed_by = $2, claimed_at = now(), heartbeat_at = now(), attempts = attempts + 1, status = 'running'
 WHERE job_id = $1
   AND status IN ('running', 'queued')
   AND claimed_by IS DISTINCT FROM $2
   AND (heartbeat_at IS NULL OR heartbeat_at < now() - ($3::double precision * interval '1 second'))
   AND attempts < $4
   AND deadline_at > now()
RETURNING job_id, label, status, attempts, claimed_by, request, response, error, aire_sent_at, false AS stale
"""

_HEARTBEAT_SQL = """
UPDATE turn_jobs SET heartbeat_at = now()
 WHERE job_id = ANY($1::text[]) AND claimed_by = $2 AND status = 'running'
RETURNING job_id
"""

_FINISH_OWNED_SQL = """
UPDATE turn_jobs SET status = $3, response = $4::jsonb, error = $5, finished_at = now()
 WHERE job_id = $1 AND claimed_by = $2 AND status = 'running'
"""

_FINISH_ANY_SQL = """
UPDATE turn_jobs SET status = $2, response = $3::jsonb, error = $4, finished_at = now()
 WHERE job_id = $1 AND status IN ('running', 'queued')
"""

_RELEASE_SQL = """
UPDATE turn_jobs SET status = 'queued', claimed_by = NULL, heartbeat_at = NULL
 WHERE claimed_by = $1 AND status = 'running'
"""

_REAP_SQL = """
WITH expired AS (
    UPDATE turn_jobs SET status = 'abandoned', finished_at = now()
     WHERE status IN ('running', 'queued') AND deadline_at < now()
    RETURNING 1
), gone AS (
    DELETE FROM turn_jobs
     WHERE status IN ('done', 'failed', 'abandoned')
       AND finished_at < now() - ($1::double precision * interval '1 second')
    RETURNING 1
)
SELECT (SELECT count(*) FROM expired) + (SELECT count(*) FROM gone)
"""

_MARK_AIRE_SENT_SQL = "UPDATE turn_jobs SET aire_sent_at = now() WHERE job_id = $1 AND aire_sent_at IS NULL"

_STALE_IDS_SQL = """
SELECT job_id FROM turn_jobs
 WHERE status IN ('running', 'queued')
   AND (heartbeat_at IS NULL OR heartbeat_at < now() - ($1::double precision * interval '1 second'))
   AND attempts < $2 AND deadline_at > now()
 ORDER BY created_at
 LIMIT $3
"""

_table_ready = False
_ddl_lock: asyncio.Lock | None = None


def _get_ddl_lock() -> asyncio.Lock:
    global _ddl_lock
    if _ddl_lock is None:
        _ddl_lock = asyncio.Lock()
    return _ddl_lock


async def _ensure_table(conn) -> None:
    global _table_ready
    if _table_ready:
        return
    async with _get_ddl_lock():
        if _table_ready:
            return
        await conn.execute(_TABLE_DDL)
        _table_ready = True


def _jsonb(value: Any) -> Any:
    if value is None or isinstance(value, dict | list):
        return value
    try:
        return json.loads(value)
    except TypeError, ValueError:
        return value


def row_from_record(record, *, me: str | None) -> LedgerRow:
    aire_sent_at = record["aire_sent_at"]
    return LedgerRow(
        ticket_id=record["job_id"],
        status=record["status"],
        attempts=record["attempts"],
        payload=_jsonb(record["request"]) or {},
        result=_jsonb(record["response"]),
        error=record["error"],
        stale=bool(record["stale"]),
        owned=(me is not None and record["claimed_by"] == me),
        extra={
            "label": record["label"],
            "claimed_by": record["claimed_by"],
            "aire_sent": aire_sent_at is not None,
        },
    )


class PgTurnLedger:
    """`TicketLedger` del runner. Cada método adquiere UNA conexión del pool
    compartido por sentencia — nunca a través de la llamada a AIRE."""

    def __init__(self, *, stale_s: float | None = None) -> None:
        self._stale_s = stale_s

    async def _run(self, op: str, fn: Callable[[Any], Awaitable[Any]]) -> Any:
        from persona_runner.mcp_tools import shared

        try:
            async with shared.acquire() as conn:
                if conn is None:
                    return None
                await _ensure_table(conn)
                return await fn(conn)
        except Exception:
            log.exception("turn_ledger_failed", op=op)
            return None

    def _stale(self) -> float:
        from persona_core import tickets

        return self._stale_s if self._stale_s is not None else tickets.STALE_S

    async def open(
        self, ticket_id: str, *, label: str, payload: dict[str, Any], deadline_s: float, claimed_by: str
    ) -> LedgerRow | None:
        async def _op(conn):
            await conn.fetchval(_OPEN_SQL, ticket_id, label, claimed_by, json.dumps(payload), float(deadline_s))
            record = await conn.fetchrow(_GET_SQL, ticket_id, self._stale())
            return row_from_record(record, me=claimed_by) if record else None

        return await self._run("open", _op)

    async def get(self, ticket_id: str) -> LedgerRow | None:
        async def _op(conn):
            record = await conn.fetchrow(_GET_SQL, ticket_id, self._stale())
            return row_from_record(record, me=None) if record else None

        return await self._run("get", _op)

    async def claim(self, ticket_id: str, *, claimed_by: str, stale_s: float, max_attempts: int) -> LedgerRow | None:
        async def _op(conn):
            record = await conn.fetchrow(_CLAIM_SQL, ticket_id, claimed_by, float(stale_s), int(max_attempts))
            return row_from_record(record, me=claimed_by) if record else None

        return await self._run("claim", _op)

    async def heartbeat(self, ticket_ids: list[str], *, claimed_by: str) -> set[str] | None:
        async def _op(conn):
            records = await conn.fetch(_HEARTBEAT_SQL, list(ticket_ids), claimed_by)
            return {r["job_id"] for r in records}

        return await self._run("heartbeat", _op)

    async def finish(
        self,
        ticket_id: str,
        *,
        claimed_by: str | None,
        status: str,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> bool | None:
        async def _op(conn):
            encoded = json.dumps(result) if result is not None else None
            if claimed_by is None:
                tag = await conn.execute(_FINISH_ANY_SQL, ticket_id, status, encoded, error)
            else:
                tag = await conn.execute(_FINISH_OWNED_SQL, ticket_id, claimed_by, status, encoded, error)
            return tag.endswith(" 1")

        return await self._run("finish", _op)

    async def release(self, *, claimed_by: str) -> int | None:
        async def _op(conn):
            tag = await conn.execute(_RELEASE_SQL, claimed_by)
            return int(tag.rsplit(" ", 1)[-1])

        return await self._run("release", _op)

    async def reap(self, *, result_ttl_s: float) -> int | None:
        async def _op(conn):
            return int(await conn.fetchval(_REAP_SQL, float(result_ttl_s)) or 0)

        return await self._run("reap", _op)

    async def mark_aire_sent(self, ticket_id: str) -> bool | None:
        async def _op(conn):
            tag = await conn.execute(_MARK_AIRE_SENT_SQL, ticket_id)
            return tag.endswith(" 1")

        return await self._run("mark_aire_sent", _op)

    async def stale_ids(self, *, stale_s: float, max_attempts: int, limit: int) -> list[str] | None:
        async def _op(conn):
            records = await conn.fetch(_STALE_IDS_SQL, float(stale_s), int(max_attempts), int(limit))
            return [r["job_id"] for r in records]

        return await self._run("stale_ids", _op)
