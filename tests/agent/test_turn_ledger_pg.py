"""`persona_runner.engine.turn_ledger` contra un Postgres REAL.

El SQL del ledger es el candado: un claim por compare-and-swap que gana
exactamente un proceso, un cierre condicionado al dueño, un latido que sólo
cuenta para el dueño vivo. Un fake no puede probar eso; esta suite corre sobre
el Postgres efímero de `tests/_pg_fixture.py` (postgresql@17 + pgvector).
"""

from __future__ import annotations

import asyncio

import pytest

from persona_runner.engine import turn_ledger
from persona_runner.engine.turn_ledger import PgTurnLedger
from persona_runner.mcp_tools import shared
from tests._pg_fixture import REQUIRES_PG

pytestmark = REQUIRES_PG


@pytest.fixture
async def ledger(postgresql_socket, monkeypatch):
    info = postgresql_socket.info
    dsn = f"postgresql://{info.user}@{info.host}:{info.port}/{info.dbname}"
    monkeypatch.setenv("POSTGRES_URL", dsn)
    shared._pool, shared._pool_lock = None, None
    turn_ledger._table_ready, turn_ledger._ddl_lock = False, None
    try:
        yield PgTurnLedger(stale_s=60.0)
    finally:
        await shared.close_pool()
        turn_ledger._table_ready, turn_ledger._ddl_lock = False, None


async def _age(ledger: PgTurnLedger, job_id: str, seconds: float = 120.0) -> None:
    async with shared.acquire() as conn:
        await conn.execute(
            "UPDATE turn_jobs SET heartbeat_at = now() - ($2::double precision * interval '1 second') WHERE job_id = $1",
            job_id,
            seconds,
        )


async def _sql(sql: str, *args):
    async with shared.acquire() as conn:
        return await conn.execute(sql, *args)


PAYLOAD = {"channel_id": "1", "user_id": "2", "user_text": "hola", "has_attachments": False}


@pytest.mark.asyncio
async def test_open_is_idempotent_and_the_row_belongs_to_the_opener(ledger):
    first = await ledger.open("j1", label="insult:1", payload=PAYLOAD, deadline_s=600, claimed_by="A")
    again = await ledger.open("j1", label="insult:1", payload={"other": 1}, deadline_s=600, claimed_by="B")
    assert first is not None and first.owned and first.status == "running" and first.attempts == 1
    assert again is not None and not again.owned and again.payload == PAYLOAD and not again.stale


@pytest.mark.asyncio
async def test_claim_is_a_compare_and_swap_with_exactly_one_winner(ledger):
    await ledger.open("j1", label="l", payload=PAYLOAD, deadline_s=600, claimed_by="A")
    assert await ledger.claim("j1", claimed_by="B", stale_s=60, max_attempts=2) is None  # latido fresco
    await _age(ledger, "j1")
    assert (await ledger.get("j1")).stale is True
    winners = await asyncio.gather(
        ledger.claim("j1", claimed_by="B", stale_s=60, max_attempts=2),
        ledger.claim("j1", claimed_by="C", stale_s=60, max_attempts=2),
    )
    won = [w for w in winners if w is not None]
    assert len(won) == 1 and won[0].attempts == 2 and won[0].owned
    await _age(ledger, "j1")
    assert await ledger.claim("j1", claimed_by="D", stale_s=60, max_attempts=2) is None  # intentos agotados


@pytest.mark.asyncio
async def test_finish_and_heartbeat_only_count_for_the_owner(ledger):
    await ledger.open("j1", label="l", payload=PAYLOAD, deadline_s=600, claimed_by="A")
    await _age(ledger, "j1")
    assert await ledger.claim("j1", claimed_by="B", stale_s=60, max_attempts=2) is not None
    assert await ledger.heartbeat(["j1"], claimed_by="A") == set()
    assert await ledger.heartbeat(["j1"], claimed_by="B") == {"j1"}
    assert await ledger.finish("j1", claimed_by="A", status="done", result={"text": "tarde"}, error=None) is False
    assert await ledger.finish("j1", claimed_by="B", status="done", result={"text": "bien"}, error=None) is True
    row = await ledger.get("j1")
    assert row.status == "done" and row.result == {"text": "bien"}
    assert await ledger.finish("j1", claimed_by="B", status="failed", result=None, error="x") is False


@pytest.mark.asyncio
async def test_release_hands_running_rows_over_and_reap_expires_and_deletes(ledger):
    await ledger.open("j1", label="l", payload=PAYLOAD, deadline_s=600, claimed_by="A")
    await ledger.open("j2", label="l", payload=PAYLOAD, deadline_s=600, claimed_by="A")
    await ledger.open("j3", label="l", payload=PAYLOAD, deadline_s=600, claimed_by="A")
    assert await ledger.finish("j3", claimed_by="A", status="done", result={}, error=None) is True
    assert await ledger.release(claimed_by="A") == 2
    row = await ledger.get("j1")
    assert row.status == "queued" and row.stale is True
    assert await ledger.stale_ids(stale_s=60, max_attempts=2, limit=10) == ["j1", "j2"]
    assert await ledger.claim("j1", claimed_by="B", stale_s=60, max_attempts=2) is not None

    await _sql("UPDATE turn_jobs SET deadline_at = now() - interval '1 second' WHERE job_id = 'j2'")
    await _sql("UPDATE turn_jobs SET finished_at = now() - interval '2 hours' WHERE job_id = 'j3'")
    assert await ledger.reap(result_ttl_s=3600) == 2
    assert (await ledger.get("j2")).status == "abandoned"
    assert await ledger.get("j3") is None


@pytest.mark.asyncio
async def test_mark_aire_sent_is_recorded_once_and_travels_in_the_row(ledger):
    await ledger.open("j1", label="l", payload=PAYLOAD, deadline_s=600, claimed_by="A")
    assert (await ledger.get("j1")).extra["aire_sent"] is False
    assert await ledger.mark_aire_sent("j1") is True
    assert await ledger.mark_aire_sent("j1") is False
    assert (await ledger.get("j1")).extra["aire_sent"] is True


@pytest.mark.asyncio
async def test_without_postgres_every_method_is_none(monkeypatch):
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    shared._pool, shared._pool_lock = None, None
    ledger = PgTurnLedger()
    assert await ledger.open("j1", label="l", payload=PAYLOAD, deadline_s=600, claimed_by="A") is None
    assert await ledger.get("j1") is None
    assert await ledger.claim("j1", claimed_by="B", stale_s=60, max_attempts=2) is None
    assert await ledger.heartbeat(["j1"], claimed_by="A") is None
    assert await ledger.finish("j1", claimed_by="A", status="done", result=None, error=None) is None
    assert await ledger.release(claimed_by="A") is None
    assert await ledger.reap(result_ttl_s=1) is None
    assert await ledger.stale_ids(stale_s=60, max_attempts=2, limit=1) is None
