"""`ResearchJobsRepository` — unit tests over mocked BaseRepository helpers.

The repo's only collaborators are the inherited `_fetchval` / `_fetch` /
`_execute` async helpers (they hit the asyncpg pool). We construct the repo
with a null manager and replace those helpers with AsyncMocks, then assert on
the SQL text + bound args and on the row→dict mapping.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import asyncpg
import pytest

from khimeras_shared.memory.repositories.research_jobs import ResearchJobsRepository


def _make_repo() -> ResearchJobsRepository:
    repo = ResearchJobsRepository(manager=None)
    repo._fetchval = AsyncMock()
    repo._fetch = AsyncMock()
    repo._execute = AsyncMock(return_value="UPDATE 1")
    return repo


class TestSaveJob:
    @pytest.mark.asyncio
    async def test_inserts_queued_and_returns_id(self):
        repo = _make_repo()
        repo._fetchval.return_value = 42
        job_id = await repo.save_job(
            channel_id="1489180895264116736",
            guild_id="1488419218302042223",
            created_by="907264175246569543",
            prompt="compara ORMs",
            persona_id="insult",
        )
        assert job_id == 42
        sql, *args = repo._fetchval.call_args.args
        assert "INSERT INTO research_jobs" in sql
        assert "'queued'" in sql
        assert "RETURNING id" in sql
        assert args[0] == "1489180895264116736"
        assert args[1] == "1488419218302042223"
        assert args[2] == "907264175246569543"
        assert args[3] == "insult"
        assert args[4] == "compara ORMs"
        assert isinstance(args[5], float)

    @pytest.mark.asyncio
    async def test_persona_id_defaults_to_none(self):
        repo = _make_repo()
        repo._fetchval.return_value = 1
        await repo.save_job(channel_id="c", guild_id=None, created_by="u", prompt="p")
        args = repo._fetchval.call_args.args[1:]
        assert args[1] is None  # guild_id
        assert args[3] is None  # persona_id

    @pytest.mark.asyncio
    async def test_raises_on_db_error(self):
        repo = _make_repo()
        repo._fetchval.side_effect = asyncpg.PostgresError("boom")
        with pytest.raises(asyncpg.PostgresError):
            await repo.save_job(channel_id="c", guild_id=None, created_by="u", prompt="p")


class TestGetPendingJobs:
    @pytest.mark.asyncio
    async def test_maps_rows_to_dicts(self):
        repo = _make_repo()
        repo._fetch.return_value = [
            {
                "id": 7,
                "channel_id": "c1",
                "guild_id": "g1",
                "created_by": "u1",
                "persona_id": "alice",
                "prompt": "tema uno",
                "retry_count": 1,
            }
        ]
        jobs = await repo.get_pending_jobs(limit=5)
        assert jobs == [
            {
                "id": 7,
                "channel_id": "c1",
                "guild_id": "g1",
                "created_by": "u1",
                "persona_id": "alice",
                "prompt": "tema uno",
                "retry_count": 1,
            }
        ]
        sql, *args = repo._fetch.call_args.args
        assert "status = 'queued'" in sql
        assert "ORDER BY created_at ASC" in sql
        assert "LIMIT $1" in sql
        assert args[0] == 5

    @pytest.mark.asyncio
    async def test_empty_queue_returns_empty_list(self):
        repo = _make_repo()
        repo._fetch.return_value = []
        assert await repo.get_pending_jobs() == []
        assert repo._fetch.call_args.args[1] == 3  # default limit


class TestStatusTransitions:
    @pytest.mark.asyncio
    async def test_mark_running(self):
        repo = _make_repo()
        await repo.mark_running(9)
        sql, *args = repo._execute.call_args.args
        assert "SET status = 'running'" in sql
        assert args[0] == 9

    @pytest.mark.asyncio
    async def test_mark_done_sets_result_and_delivered_at(self):
        repo = _make_repo()
        await repo.mark_done(9, "el reporte")
        sql, *args = repo._execute.call_args.args
        assert "SET status = 'done'" in sql
        assert "result = $1" in sql
        assert "delivered_at = $2" in sql
        assert args[0] == "el reporte"
        assert isinstance(args[1], float)
        assert args[2] == 9

    @pytest.mark.asyncio
    async def test_mark_failed_bumps_retry(self):
        repo = _make_repo()
        await repo.mark_failed(9)
        sql, *args = repo._execute.call_args.args
        assert "SET status = 'failed'" in sql
        assert "retry_count = retry_count + 1" in sql
        assert args[0] == 9

    @pytest.mark.asyncio
    async def test_requeue_bumps_retry(self):
        repo = _make_repo()
        await repo.requeue(9)
        sql, *args = repo._execute.call_args.args
        assert "SET status = 'queued'" in sql
        assert "retry_count = retry_count + 1" in sql
        assert args[0] == 9

    @pytest.mark.asyncio
    async def test_status_transitions_swallow_db_errors(self):
        repo = _make_repo()
        repo._execute.side_effect = asyncpg.PostgresError("down")
        await repo.mark_running(1)
        await repo.mark_done(1, "r")
        await repo.mark_failed(1)
        await repo.requeue(1)


class TestResetStaleRunning:
    @pytest.mark.asyncio
    async def test_returns_recovered_count(self):
        repo = _make_repo()
        repo._execute.return_value = "UPDATE 4"
        recovered = await repo.reset_stale_running(older_than_s=600.0)
        assert recovered == 4
        sql, *args = repo._execute.call_args.args
        assert "SET status = 'queued'" in sql
        assert "status = 'running'" in sql
        assert "created_at < $1" in sql
        assert isinstance(args[0], float)

    @pytest.mark.asyncio
    async def test_db_error_returns_zero(self):
        repo = _make_repo()
        repo._execute.side_effect = asyncpg.PostgresError("down")
        assert await repo.reset_stale_running(older_than_s=600.0) == 0
