"""`AgendasRepository` — unit tests over mocked BaseRepository helpers.

The repo's only collaborators are the inherited `_fetchval` / `_fetch` /
`_execute` async helpers (they hit the asyncpg pool). We construct the repo
with a null manager and replace those helpers with AsyncMocks, then assert on
the SQL text + bound args and on the row→dict mapping.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import asyncpg
import pytest

from khimeras_shared.memory.repositories.agendas import AgendasRepository


def _make_repo() -> AgendasRepository:
    repo = AgendasRepository(manager=None)
    repo._fetchval = AsyncMock()
    repo._fetch = AsyncMock()
    repo._execute = AsyncMock(return_value="UPDATE 1")
    return repo


class TestSaveAgenda:
    @pytest.mark.asyncio
    async def test_inserts_active_and_returns_id(self):
        repo = _make_repo()
        repo._fetchval.return_value = 42
        agenda_id = await repo.save_agenda(
            persona_id="vultur",
            channel_id="1489180895264116736",
            guild_id="1488419218302042223",
            created_by="907264175246569543",
            goal="vigila estrenos de A24",
            cadence_hours=12,
        )
        assert agenda_id == 42
        sql, *args = repo._fetchval.call_args.args
        assert "INSERT INTO agendas" in sql
        assert "RETURNING id" in sql
        assert "active" in sql
        assert args[0] == "vultur"
        assert args[1] == "1489180895264116736"
        assert args[2] == "1488419218302042223"
        assert args[3] == "907264175246569543"
        assert args[4] == "vigila estrenos de A24"
        assert args[5] == 12
        assert isinstance(args[6], float)

    @pytest.mark.asyncio
    async def test_cadence_defaults_to_24(self):
        repo = _make_repo()
        repo._fetchval.return_value = 1
        await repo.save_agenda(
            persona_id="insult",
            channel_id="c",
            guild_id=None,
            created_by="u",
            goal="g",
        )
        args = repo._fetchval.call_args.args[1:]
        assert args[2] is None  # guild_id
        assert args[5] == 24  # cadence_hours default

    @pytest.mark.asyncio
    async def test_raises_on_db_error(self):
        repo = _make_repo()
        repo._fetchval.side_effect = asyncpg.PostgresError("boom")
        with pytest.raises(asyncpg.PostgresError):
            await repo.save_agenda(
                persona_id="insult",
                channel_id="c",
                guild_id=None,
                created_by="u",
                goal="g",
            )


class TestGetDueAgendas:
    @pytest.mark.asyncio
    async def test_maps_rows_to_dicts(self):
        repo = _make_repo()
        repo._fetch.return_value = [
            {
                "id": 7,
                "persona_id": "alice",
                "channel_id": "c1",
                "guild_id": "g1",
                "created_by": "u1",
                "goal": "tema uno",
                "cadence_hours": 24.0,
                "last_run_at": None,
            }
        ]
        agendas = await repo.get_due_agendas(now=1000.0, limit=5)
        assert agendas == [
            {
                "id": 7,
                "persona_id": "alice",
                "channel_id": "c1",
                "guild_id": "g1",
                "created_by": "u1",
                "goal": "tema uno",
                "cadence_hours": 24.0,
                "last_run_at": None,
            }
        ]
        sql, *args = repo._fetch.call_args.args
        assert "active = 1" in sql
        assert "last_run_at IS NULL OR last_run_at + cadence_hours * 3600 <= $1" in sql
        assert "LIMIT $2" in sql
        assert args[0] == 1000.0
        assert args[1] == 5

    @pytest.mark.asyncio
    async def test_no_due_returns_empty_list(self):
        repo = _make_repo()
        repo._fetch.return_value = []
        assert await repo.get_due_agendas(now=1.0) == []
        assert repo._fetch.call_args.args[2] == 3  # default limit

    @pytest.mark.asyncio
    async def test_persona_filter_binds_persona_id(self):
        repo = _make_repo()
        repo._fetch.return_value = []
        await repo.get_due_agendas(now=500.0, limit=2, persona_id="vultur")
        sql, *args = repo._fetch.call_args.args
        assert "persona_id = $3" in sql
        assert args[0] == 500.0
        assert args[1] == 2
        assert args[2] == "vultur"


class TestMarkAndDeactivate:
    @pytest.mark.asyncio
    async def test_mark_agenda_ran(self):
        repo = _make_repo()
        await repo.mark_agenda_ran(9, now=1234.5)
        sql, *args = repo._execute.call_args.args
        assert "SET last_run_at = $1" in sql
        assert args[0] == 1234.5
        assert args[1] == 9

    @pytest.mark.asyncio
    async def test_deactivate_agenda(self):
        repo = _make_repo()
        await repo.deactivate_agenda(9)
        sql, *args = repo._execute.call_args.args
        assert "SET active = 0" in sql
        assert args[0] == 9

    @pytest.mark.asyncio
    async def test_writes_swallow_db_errors(self):
        repo = _make_repo()
        repo._execute.side_effect = asyncpg.PostgresError("down")
        await repo.mark_agenda_ran(1, now=1.0)
        await repo.deactivate_agenda(1)


class TestGetChannelAgendas:
    @pytest.mark.asyncio
    async def test_maps_rows_and_binds_channel(self):
        repo = _make_repo()
        repo._fetch.return_value = [
            {
                "id": 3,
                "persona_id": "insult",
                "channel_id": "c9",
                "guild_id": None,
                "created_by": "u9",
                "goal": "vigila X",
                "cadence_hours": 6.0,
                "last_run_at": 999.0,
            }
        ]
        agendas = await repo.get_channel_agendas("c9")
        assert agendas[0]["goal"] == "vigila X"
        assert agendas[0]["last_run_at"] == 999.0
        sql, *args = repo._fetch.call_args.args
        assert "channel_id = $1" in sql
        assert "active = 1" in sql
        assert args[0] == "c9"
