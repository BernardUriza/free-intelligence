"""`invite_turns` contra un Postgres REAL — la fila del boleto del gateway.

El schema canónico (`postgres_schema.sql`) crea la tabla; aquí se prueba que el
claim gana exactamente un proceso, que el cierre y el latido sólo cuentan para
el dueño, que las etapas y los ids entregados aterrizan, y que el reaper
abandona por deadline y borra lo viejo.
"""

from __future__ import annotations

import asyncio

import pytest

from tests._pg_fixture import REQUIRES_PG

pytestmark = REQUIRES_PG

PAYLOAD = {"channel_id": "123", "reason": "ven", "persona_id": "insult"}


@pytest.fixture
async def ledger(pg_memory_store):
    repo = pg_memory_store.invite_turn_ledger
    repo._stale_s = 60.0
    return repo


async def _age(pg_memory_store, turn_id: str) -> None:
    await pg_memory_store._invite_turns._execute(
        "UPDATE invite_turns SET heartbeat_at = now() - interval '2 minutes' WHERE turn_id = $1", turn_id
    )


@pytest.mark.asyncio
async def test_open_is_idempotent_and_the_stage_starts_at_accepted(ledger):
    first = await ledger.open("t1", label="123", payload=PAYLOAD, deadline_s=600, claimed_by="A")
    again = await ledger.open("t1", label="123", payload={"x": 1}, deadline_s=600, claimed_by="B")
    assert first.owned and first.extra["stage"] == "accepted" and first.attempts == 1
    assert not again.owned and again.payload == PAYLOAD and not again.stale


@pytest.mark.asyncio
async def test_claim_has_exactly_one_winner_and_respects_the_attempt_cap(pg_memory_store, ledger):
    await ledger.open("t1", label="123", payload=PAYLOAD, deadline_s=600, claimed_by="A")
    assert await ledger.claim("t1", claimed_by="B", stale_s=60, max_attempts=2) is None
    await _age(pg_memory_store, "t1")
    winners = await asyncio.gather(
        ledger.claim("t1", claimed_by="B", stale_s=60, max_attempts=2),
        ledger.claim("t1", claimed_by="C", stale_s=60, max_attempts=2),
    )
    assert len([w for w in winners if w is not None]) == 1
    await _age(pg_memory_store, "t1")
    assert await ledger.claim("t1", claimed_by="D", stale_s=60, max_attempts=2) is None


@pytest.mark.asyncio
async def test_stages_delivery_and_outcome_land_in_the_row(pg_memory_store, ledger):
    await ledger.open("t1", label="123", payload=PAYLOAD, deadline_s=600, claimed_by="A")
    assert await ledger.advance_stage("t1", "runner_done", text="hola [REMEMBER: x]", tail={"user_id": "9"}) is True
    assert await ledger.advance_stage("t1", "markers_done", text="hola") is True
    row = await ledger.get("t1")
    assert row.extra["stage"] == "markers_done" and row.extra["stage_text"] == "hola"
    assert row.extra["tail"] == {"user_id": "9"}  # el tail sobrevive a una etapa sin tail
    assert await ledger.mark_delivered("t1", [1552311706619740314, 7], partial=True) is True
    assert await ledger.finish("t1", claimed_by="A", status="done", result={"outcome": "delivered"}, error=None) is True
    row = await ledger.get("t1")
    assert row.status == "done" and row.result == {"outcome": "delivered"} and row.extra["stage"] == "delivered"
    assert row.extra["delivered_message_ids"] == [1552311706619740314, 7] and row.extra["partial"] is True


@pytest.mark.asyncio
async def test_finish_and_heartbeat_only_count_for_the_owner(pg_memory_store, ledger):
    await ledger.open("t1", label="123", payload=PAYLOAD, deadline_s=600, claimed_by="A")
    await _age(pg_memory_store, "t1")
    assert await ledger.claim("t1", claimed_by="B", stale_s=60, max_attempts=2) is not None
    assert await ledger.heartbeat(["t1"], claimed_by="A") == set()
    assert await ledger.heartbeat(["t1"], claimed_by="B") == {"t1"}
    assert (
        await ledger.finish("t1", claimed_by="A", status="done", result={"outcome": "delivered"}, error=None) is False
    )
    assert await ledger.finish("t1", claimed_by="B", status="done", result={"outcome": "empty"}, error=None) is True


@pytest.mark.asyncio
async def test_release_and_reap(pg_memory_store, ledger):
    await ledger.open("t1", label="123", payload=PAYLOAD, deadline_s=600, claimed_by="A")
    await ledger.open("t2", label="123", payload=PAYLOAD, deadline_s=600, claimed_by="A")
    assert await ledger.release(claimed_by="A") == 2
    assert (await ledger.get("t1")).status == "queued"
    assert await ledger.stale_ids(stale_s=60, max_attempts=2, limit=10) == ["t1", "t2"]
    await pg_memory_store._invite_turns._execute(
        "UPDATE invite_turns SET deadline_at = now() - interval '1 second' WHERE turn_id = 't2'"
    )
    assert await ledger.reap(result_ttl_s=3600) == 1
    assert (await ledger.get("t2")).extra["stage"] == "abandoned"
