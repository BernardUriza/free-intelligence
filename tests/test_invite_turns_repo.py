"""`InviteTurnsRepository` — el SQL que viaja y el fail-soft, sin Postgres.

El candado real (CAS, cierre condicionado) se prueba contra Postgres en
`tests/core/test_invite_turns_pg.py`; aquí sólo que cada método manda la
sentencia y los argumentos correctos, y que CUALQUIER excepción (incluida la de
"pool no conectado") vuelve como None en vez de tumbar el invite.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from khimeras_shared.memory.repositories.invite_turns import InviteTurnsRepository


def _repo() -> InviteTurnsRepository:
    repo = InviteTurnsRepository(manager=None, stale_s=60.0)
    repo._execute = AsyncMock(return_value="UPDATE 1")
    repo._fetch = AsyncMock(return_value=[])
    repo._fetchrow = AsyncMock(return_value=None)
    repo._fetchval = AsyncMock(return_value=0)
    return repo


@pytest.mark.asyncio
async def test_open_inserts_with_on_conflict_and_reads_the_row_back():
    repo = _repo()
    await repo.open("t1", label="123", payload={"reason": "ven"}, deadline_s=600, claimed_by="me")
    sql, *args = repo._execute.await_args.args
    assert "ON CONFLICT (turn_id) DO NOTHING" in sql
    assert args[0] == "t1" and args[2] == "me" and args[4] == 600.0
    assert "reason" in args[3]
    assert repo._fetchrow.await_args.args[1] == "t1"


@pytest.mark.asyncio
async def test_claim_is_conditional_on_owner_staleness_attempts_and_deadline():
    repo = _repo()
    await repo.claim("t1", claimed_by="me", stale_s=60, max_attempts=2)
    sql, *args = repo._fetchrow.await_args.args
    for clause in ("claimed_by IS DISTINCT FROM $2", "attempts < $4", "deadline_at > now()", "heartbeat_at IS NULL OR"):
        assert clause in sql
    assert args == ["t1", "me", 60.0, 2]


@pytest.mark.asyncio
async def test_finish_owned_versus_unconditional_and_the_stage_follows_the_outcome():
    repo = _repo()
    assert await repo.finish("t1", claimed_by="me", status="done", result={"outcome": "delivered"}, error=None) is True
    sql, *args = repo._execute.await_args.args
    assert "claimed_by = $2 AND status = 'running'" in sql and args[-1] == "delivered"
    await repo.finish("t1", claimed_by=None, status="failed", result=None, error="attempts_exhausted")
    sql, *args = repo._execute.await_args.args
    assert "claimed_by" not in sql.split("WHERE", 1)[1] and args[-1] == "failed"
    repo._execute = AsyncMock(return_value="UPDATE 0")
    assert await repo.finish("t1", claimed_by="otro", status="done", result={}, error=None) is False


@pytest.mark.asyncio
async def test_stage_and_delivery_writes_carry_text_tail_and_ids():
    repo = _repo()
    await repo.advance_stage("t1", "runner_done", text="hola", tail={"user_id": "9"})
    sql, *args = repo._execute.await_args.args
    assert "SET stage = $2" in sql and args[:3] == ["t1", "runner_done", "hola"] and '"user_id"' in args[3]
    await repo.mark_delivered("t1", [11, 22], partial=True)
    sql, *args = repo._execute.await_args.args
    assert "delivered_message_ids = $2::bigint[]" in sql and args == ["t1", [11, 22], True]


@pytest.mark.asyncio
async def test_any_fault_including_a_pool_not_connected_is_none_never_a_500():
    repo = InviteTurnsRepository(manager=None)  # _pool levanta RuntimeError: no conectado
    assert await repo.open("t1", label="l", payload={}, deadline_s=1, claimed_by="me") is None
    assert await repo.get("t1") is None
    assert await repo.claim("t1", claimed_by="me", stale_s=1, max_attempts=2) is None
    assert await repo.heartbeat(["t1"], claimed_by="me") is None
    assert await repo.finish("t1", claimed_by="me", status="done", result=None, error=None) is None
    assert await repo.release(claimed_by="me") is None
    assert await repo.reap(result_ttl_s=1) is None
    assert await repo.advance_stage("t1", "sending") is None
    assert await repo.mark_delivered("t1", [1]) is None
    assert await repo.stale_ids(stale_s=1, max_attempts=2, limit=1) is None
