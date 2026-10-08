"""RemindersRepository.list_pending / cancel_pending — the cancel is a RETIRE,
never a DELETE, and it can only reach the asking user's rows owned by the
emitting persona (the drain loop's isolation contract, applied to cancellation).

SQL-boundary tests: `_fetch`/`_execute` are stubbed on the instance so the
matching/isolation logic (which lives in Python) is exercised against the exact
statements the repo would send to Postgres.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import asyncpg

from persona_core.memory.repositories.reminders import RemindersRepository


def _row(reminder_id: int, description: str, *, remind_at: float = 1000.0, recurring: str = "none") -> dict:
    return {
        "id": reminder_id,
        "channel_id": "C1",
        "guild_id": "G1",
        "created_by": "U1",
        "description": description,
        "remind_at": remind_at,
        "recurring": recurring,
        "persona_id": "vultur",
    }


def _repo(rows: list[dict]) -> RemindersRepository:
    repo = RemindersRepository(MagicMock())
    repo._fetch = AsyncMock(return_value=rows)
    repo._execute = AsyncMock(return_value=f"UPDATE {len(rows)}")
    return repo


# --------------------------------------------------------------------------
# list_pending
# --------------------------------------------------------------------------


async def test_list_pending_queries_by_user_and_persona():
    repo = _repo([_row(1, "sacar la ropa")])

    pending = await repo.list_pending("U1", "vultur")

    sql = repo._fetch.await_args.args[0]
    assert "delivered = 0" in sql
    assert "created_by" in sql and "persona_id" in sql
    assert repo._fetch.await_args.args[1:] == ("U1", "vultur")
    assert pending[0]["description"] == "sacar la ropa"


# --------------------------------------------------------------------------
# cancel_pending
# --------------------------------------------------------------------------


async def test_cancel_matches_case_insensitive_substring_and_retires_only_those_ids():
    repo = _repo([_row(1, "Sacar la ROPA de la lavadora"), _row(2, "tomar el ARV"), _row(3, "ropa al tinte")])

    cancelled = await repo.cancel_pending("U1", "vultur", "ropa")

    assert [r["id"] for r in cancelled] == [1, 3]
    sql = repo._execute.await_args.args[0]
    assert "SET delivered = 1" in sql
    assert "DELETE" not in sql.upper()  # append-only: cancel retires, never removes
    assert repo._execute.await_args.args[1] == [1, 3]


async def test_cancel_no_match_touches_nothing():
    """RESISTANCE: a criterion that matches no row must not fire an UPDATE."""
    repo = _repo([_row(1, "tomar el ARV")])

    assert await repo.cancel_pending("U1", "vultur", "ropa") == []
    repo._execute.assert_not_awaited()


async def test_cancel_empty_criterion_cancels_nothing():
    """RESISTANCE: an empty substring matches EVERYTHING — the guard refuses the
    accidental cancel-all before even reading the table."""
    repo = _repo([_row(1, "tomar el ARV")])

    assert await repo.cancel_pending("U1", "vultur", "") == []
    assert await repo.cancel_pending("U1", "vultur", "   ") == []
    repo._fetch.assert_not_awaited()
    repo._execute.assert_not_awaited()


async def test_cancel_scopes_the_read_to_user_and_persona():
    """The match pool is list_pending(created_by, persona_id) — the isolation is
    in the SELECT, so a criterion can never see another user's/persona's rows."""
    repo = _repo([])

    await repo.cancel_pending("U1", "vultur", "ropa")

    assert repo._fetch.await_args.args[1:] == ("U1", "vultur")


async def test_cancel_survives_a_pg_fault_and_returns_empty():
    """RESISTANCE: best-effort — a dead table logs and yields [], never raises
    (the turn already carried the persona's ack)."""
    repo = _repo([_row(1, "sacar la ropa")])
    repo._execute = AsyncMock(side_effect=asyncpg.PostgresError("pg down"))

    assert await repo.cancel_pending("U1", "vultur", "ropa") == []


async def test_cancel_of_a_recurring_reminder_retires_it():
    """delivered=1 fully stops a recurring row: the drain only rolls forward
    rows still at delivered=0, so the recurrence dies with the cancel."""
    repo = _repo([_row(5, "tomar el ARV", recurring="daily")])

    cancelled = await repo.cancel_pending("U1", "vultur", "arv")

    assert [r["id"] for r in cancelled] == [5]
    assert "SET delivered = 1" in repo._execute.await_args.args[0]


async def test_cancel_criterion_quoted_from_the_context_block_still_matches():
    """RESISTANCE of the GRAVE class: the turn-context block renders rows as
    «description», so a persona quoting the fragment verbatim emits
    [REMIND_CANCEL: «la ropa»]. The surrounding quotes must be stripped from the
    needle — otherwise the cancel silently no-ops right after the persona said
    "va, muerto", and the reminder rings anyway."""
    repo = _repo([_row(1, "sacar la ropa de la lavadora")])

    for quoted in ("\u00abla ropa\u00bb", '"la ropa"', "'la ropa'", "\u201cla ropa\u201d", "\u2018la ropa\u2019"):
        repo._execute.reset_mock()
        cancelled = await repo.cancel_pending("U1", "vultur", quoted)
        assert [r["id"] for r in cancelled] == [1], f"quoted criterion {quoted!r} failed to match"


async def test_cancel_quotes_only_stripped_at_the_edges():
    """Interior quote chars are content, not wrapping — they still count for the
    substring match."""
    repo = _repo([_row(1, 'ver la peli "Hereditary" con Alex')])

    cancelled = await repo.cancel_pending("U1", "vultur", '"Hereditary"')

    assert [r["id"] for r in cancelled] == [1]


async def test_cancel_criterion_that_is_only_quotes_cancels_nothing():
    """RESISTANCE: «» alone strips down to empty — the cancel-all guard must
    still refuse it after quote-stripping."""
    repo = _repo([_row(1, "sacar la ropa")])

    assert await repo.cancel_pending("U1", "vultur", "«»") == []
    repo._fetch.assert_not_awaited()
    repo._execute.assert_not_awaited()
