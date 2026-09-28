"""Invite turns — la fila del boleto del gateway (`persona_core.tickets.TicketLedger`).

Implementa el protocolo del ledger (open/get/claim/heartbeat/finish/release/reap)
sobre `invite_turns`, más los dos escritos de dominio que hacen posible reanudar
por ETAPA en vez de re-correr el turno: `advance_stage` (la respuesta del runner
o el texto tras los marcadores, con el contexto de cola que la entrega
necesita) y `mark_delivered` (los ids de Discord que sí salieron).

Todo es best-effort: atrapa `Exception`, no sólo `PostgresError`, porque el API
de invites se levanta ANTES de que `memory.connect()` termine (`app.py`) y un
invite en esa ventana tiene que degradar a RAM, nunca dar 500.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from persona_core.memory.base import BaseRepository
from persona_core.tickets import LedgerRow

log = structlog.get_logger()

_COLS = (
    "turn_id, label, status, attempts, claimed_by, request, result, error, "
    "stage, stage_text, tail, delivered_message_ids, partial"
)

_OPEN_SQL = """
INSERT INTO invite_turns (turn_id, label, status, attempts, claimed_by, request, claimed_at, heartbeat_at, deadline_at)
VALUES ($1, $2, 'running', 1, $3, $4::jsonb, now(), now(), now() + ($5::double precision * interval '1 second'))
ON CONFLICT (turn_id) DO NOTHING
"""

_GET_SQL = (
    "SELECT "
    + _COLS
    + ", (heartbeat_at IS NULL OR heartbeat_at < now() - ($2::double precision * interval '1 second')) AS stale "
    "FROM invite_turns WHERE turn_id = $1"
)

_CLAIM_SQL = (
    "UPDATE invite_turns "
    "SET claimed_by = $2, claimed_at = now(), heartbeat_at = now(), attempts = attempts + 1, status = 'running' "
    "WHERE turn_id = $1 AND status IN ('running', 'queued') AND claimed_by IS DISTINCT FROM $2 "
    "AND (heartbeat_at IS NULL OR heartbeat_at < now() - ($3::double precision * interval '1 second')) "
    "AND attempts < $4 AND deadline_at > now() "
    "RETURNING " + _COLS + ", false AS stale"
)

_HEARTBEAT_SQL = (
    "UPDATE invite_turns SET heartbeat_at = now() "
    "WHERE turn_id = ANY($1::text[]) AND claimed_by = $2 AND status = 'running' RETURNING turn_id"
)

_FINISH_OWNED_SQL = (
    "UPDATE invite_turns SET status = $3, result = $4::jsonb, error = $5, finished_at = now(), "
    "stage = CASE WHEN $6::text IS NULL THEN stage ELSE $6::text END "
    "WHERE turn_id = $1 AND claimed_by = $2 AND status = 'running'"
)

_FINISH_ANY_SQL = (
    "UPDATE invite_turns SET status = $2, result = $3::jsonb, error = $4, finished_at = now(), "
    "stage = CASE WHEN $5::text IS NULL THEN stage ELSE $5::text END "
    "WHERE turn_id = $1 AND status IN ('running', 'queued')"
)

_RELEASE_SQL = (
    "UPDATE invite_turns SET status = 'queued', claimed_by = NULL, heartbeat_at = NULL "
    "WHERE claimed_by = $1 AND status = 'running'"
)

_REAP_SQL = """
WITH expired AS (
    UPDATE invite_turns SET status = 'abandoned', stage = 'abandoned', finished_at = now()
     WHERE status IN ('running', 'queued') AND deadline_at < now()
    RETURNING 1
), gone AS (
    DELETE FROM invite_turns
     WHERE status IN ('done', 'failed', 'abandoned')
       AND finished_at < now() - ($1::double precision * interval '1 second')
    RETURNING 1
)
SELECT (SELECT count(*) FROM expired) + (SELECT count(*) FROM gone)
"""

_STAGE_SQL = (
    "UPDATE invite_turns SET stage = $2, "
    "stage_text = CASE WHEN $3::text IS NULL THEN stage_text ELSE $3::text END, "
    "tail = CASE WHEN $4::jsonb IS NULL THEN tail ELSE $4::jsonb END "
    "WHERE turn_id = $1"
)

_DELIVERED_SQL = (
    "UPDATE invite_turns SET stage = 'delivered', delivered_message_ids = $2::bigint[], partial = $3 WHERE turn_id = $1"
)

_STALE_IDS_SQL = (
    "SELECT turn_id FROM invite_turns WHERE status IN ('running', 'queued') "
    "AND (heartbeat_at IS NULL OR heartbeat_at < now() - ($1::double precision * interval '1 second')) "
    "AND attempts < $2 AND deadline_at > now() ORDER BY created_at LIMIT $3"
)

STAGE_OUTCOMES = frozenset({"delivered", "empty", "failed", "uncertain"})


def _jsonb(value: Any) -> Any:
    if value is None or isinstance(value, dict | list):
        return value
    try:
        return json.loads(value)
    except TypeError, ValueError:
        return value


def _rows(tag: str) -> int:
    try:
        return int(tag.rsplit(" ", 1)[-1])
    except ValueError, AttributeError:
        return 0


def row_from_record(record, *, me: str | None) -> LedgerRow:
    return LedgerRow(
        ticket_id=record["turn_id"],
        status=record["status"],
        attempts=record["attempts"],
        payload=_jsonb(record["request"]) or {},
        result=_jsonb(record["result"]),
        error=record["error"],
        stale=bool(record["stale"]),
        owned=(me is not None and record["claimed_by"] == me),
        extra={
            "label": record["label"],
            "claimed_by": record["claimed_by"],
            "stage": record["stage"],
            "stage_text": record["stage_text"],
            "tail": _jsonb(record["tail"]) or {},
            "delivered_message_ids": list(record["delivered_message_ids"] or []),
            "partial": bool(record["partial"]),
        },
    )


class InviteTurnsRepository(BaseRepository):
    """Owns the `invite_turns` table. Every method returns `None` on any fault."""

    def __init__(self, manager, *, stale_s: float | None = None) -> None:
        super().__init__(manager)
        self._stale_s = stale_s

    def _stale(self) -> float:
        from persona_core import tickets

        return self._stale_s if self._stale_s is not None else tickets.STALE_S

    async def _guard(self, op: str, coro):
        try:
            return await coro
        except Exception:
            log.warning("invite_turns_ledger_failed", op=op, exc_info=True)
            return None

    # -- TicketLedger --

    async def open(
        self, ticket_id: str, *, label: str, payload: dict[str, Any], deadline_s: float, claimed_by: str
    ) -> LedgerRow | None:
        async def _op():
            await self._execute(_OPEN_SQL, ticket_id, label, claimed_by, json.dumps(payload), float(deadline_s))
            record = await self._fetchrow(_GET_SQL, ticket_id, self._stale())
            return row_from_record(record, me=claimed_by) if record else None

        return await self._guard("open", _op())

    async def get(self, ticket_id: str) -> LedgerRow | None:
        async def _op():
            record = await self._fetchrow(_GET_SQL, ticket_id, self._stale())
            return row_from_record(record, me=None) if record else None

        return await self._guard("get", _op())

    async def claim(self, ticket_id: str, *, claimed_by: str, stale_s: float, max_attempts: int) -> LedgerRow | None:
        async def _op():
            record = await self._fetchrow(_CLAIM_SQL, ticket_id, claimed_by, float(stale_s), int(max_attempts))
            return row_from_record(record, me=claimed_by) if record else None

        return await self._guard("claim", _op())

    async def heartbeat(self, ticket_ids: list[str], *, claimed_by: str) -> set[str] | None:
        async def _op():
            records = await self._fetch(_HEARTBEAT_SQL, list(ticket_ids), claimed_by)
            return {r["turn_id"] for r in records}

        return await self._guard("heartbeat", _op())

    async def finish(
        self,
        ticket_id: str,
        *,
        claimed_by: str | None,
        status: str,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> bool | None:
        async def _op():
            encoded = json.dumps(result) if result is not None else None
            outcome = (result or {}).get("outcome") if status == "done" else "failed"
            stage = outcome if outcome in STAGE_OUTCOMES else None
            if claimed_by is None:
                tag = await self._execute(_FINISH_ANY_SQL, ticket_id, status, encoded, error, stage)
            else:
                tag = await self._execute(_FINISH_OWNED_SQL, ticket_id, claimed_by, status, encoded, error, stage)
            return _rows(tag) == 1

        return await self._guard("finish", _op())

    async def release(self, *, claimed_by: str) -> int | None:
        async def _op():
            return _rows(await self._execute(_RELEASE_SQL, claimed_by))

        return await self._guard("release", _op())

    async def reap(self, *, result_ttl_s: float) -> int | None:
        async def _op():
            return int(await self._fetchval(_REAP_SQL, float(result_ttl_s)) or 0)

        return await self._guard("reap", _op())

    # -- Dominio --

    async def advance_stage(
        self, turn_id: str, stage: str, *, text: str | None = None, tail: dict[str, Any] | None = None
    ) -> bool | None:
        async def _op():
            encoded = json.dumps(tail) if tail is not None else None
            return _rows(await self._execute(_STAGE_SQL, turn_id, stage, text, encoded)) == 1

        return await self._guard("advance_stage", _op())

    async def mark_delivered(self, turn_id: str, message_ids: list[int], *, partial: bool = False) -> bool | None:
        async def _op():
            return _rows(await self._execute(_DELIVERED_SQL, turn_id, [int(i) for i in message_ids], partial)) == 1

        return await self._guard("mark_delivered", _op())

    async def stale_ids(self, *, stale_s: float, max_attempts: int, limit: int) -> list[str] | None:
        async def _op():
            records = await self._fetch(_STALE_IDS_SQL, float(stale_s), int(max_attempts), int(limit))
            return [r["turn_id"] for r in records]

        return await self._guard("stale_ids", _op())
