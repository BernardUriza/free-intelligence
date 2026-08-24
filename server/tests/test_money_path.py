"""A real turn must leave a row — the join nothing tested until now.

`test_spend.py` proves the table works. `test_ledger_rebirth.py` proves the
counter forgets a dead client. Neither joins them, and the join is where the
money actually travels: drain → `turn_cost` → `Ledger.account` → the delta →
`spend.bank` → Postgres. The eviction bug lived in exactly that gap and passed
every test in the suite.

So this drives the REAL `run_turn` — the rotor loop, `_attempt`, the pool, the
result seam — against a stub that stands in for the `claude` subprocess and a
real Postgres. Everything between the SDK's messages and the row is the code
that ships.
"""

import os
from typing import Any

import asyncpg
import pytest

from aire import spend
from aire.engine.contract import TurnSpec
from aire.engine.core import Engine
from aire.engine.turn import run_turn

DSN = os.environ.get("AIRE_DATABASE_URL", "postgresql://bernardurizaorozco@127.0.0.1:5432/aire")


class TextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class AssistantMessage:
    """Named for `drain`, which identifies messages by `type(m).__name__`."""

    def __init__(self, text: str) -> None:
        self.content = [TextBlock(text)]
        self.model = "claude-haiku-4-5-20251001"


class ResultMessage:
    def __init__(self, cumulative: float) -> None:
        self.usage = {"input_tokens": 10, "output_tokens": 42,
                      "cache_read_input_tokens": 13605}
        self.total_cost_usd = cumulative  # the CLIENT's cumulative, as the SDK reports it
        self.session_id = "0ad1b2c3-0000-5000-8000-000000000001"


class FakeClient:
    """One `claude` subprocess that never existed. `cumulative` is what the SDK
    would report after each turn on THIS client — it only ever grows."""

    def __init__(self, costs: list[float]) -> None:
        self.costs = list(costs)

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *_: Any) -> bool:
        return False

    async def query(self, _payload: Any) -> None:
        return None

    async def receive_response(self) -> Any:
        yield AssistantMessage("PONG")
        yield ResultMessage(self.costs.pop(0))


class Slot:
    name = "primary"
    env: dict = {}


class Rotor:
    def active(self) -> Slot:
        return Slot()

    def burn(self, _name: str) -> None:
        raise AssertionError("a healthy turn must not burn a credential slot")


class NoMemory:
    async def load(self, *_: Any, **__: Any) -> list:
        return []


async def _rows() -> list:
    """No rows and no TABLE are the same answer here: if nothing banked, nothing
    created it either. Reading it as an empty list makes the failure say "a paid
    turn left no trace" instead of "relation does not exist" — a red that names
    the defect rather than the plumbing."""
    conn = await asyncpg.connect(DSN, timeout=10)
    try:
        return await conn.fetch(
            "SELECT door, project, session, usd FROM aire_spend ORDER BY seq")
    except asyncpg.exceptions.UndefinedTableError:
        return []
    finally:
        await conn.close()


async def _wired(monkeypatch, tmp_path, costs: list[float]) -> Engine:
    import aire.engine.core as core

    conn = await asyncpg.connect(DSN, timeout=10)
    await conn.execute("DROP TABLE IF EXISTS aire_spend")
    await conn.close()
    spend._ready = False
    monkeypatch.setattr(core, "WORKSPACES", tmp_path)
    monkeypatch.setattr(core, "build_options", lambda *a, **k: None)
    client = FakeClient(costs)
    monkeypatch.setattr(core, "ClaudeSDKClient", lambda options=None: client)
    engine = Engine(NoMemory())
    engine.rotor = Rotor()
    return engine


async def _run(engine: Engine, prompt: str) -> list:
    return [ev async for ev in
            run_turn(engine, "canary", "s1", prompt, TurnSpec(mode="complete"))]


@pytest.mark.asyncio
async def test_a_turn_leaves_a_row_for_what_it_cost(monkeypatch, tmp_path) -> None:
    engine = await _wired(monkeypatch, tmp_path, [0.028])
    events = await _run(engine, "hi")
    assert [e["type"] for e in events] == ["text", "result"]

    rows = await _rows()
    assert len(rows) == 1, "a paid turn left no trace in aire_spend"
    assert rows[0]["usd"] == pytest.approx(0.028)
    assert (rows[0]["door"], rows[0]["project"], rows[0]["session"]) == ("engine", "canary", "s1")


@pytest.mark.asyncio
async def test_a_second_turn_banks_the_delta_not_the_total(monkeypatch, tmp_path) -> None:
    """`total_cost_usd` is CUMULATIVE. Banking it whole would charge the first
    turn again on the second — the month would inflate instead of skip."""
    engine = await _wired(monkeypatch, tmp_path, [0.028, 0.030])
    await _run(engine, "hi")
    await _run(engine, "again")

    rows = await _rows()
    assert [float(r["usd"]) for r in rows] == pytest.approx([0.028, 0.002])
    assert await spend.month_to_date() == pytest.approx(0.030)


@pytest.mark.asyncio
async def test_an_evicted_session_still_banks_its_next_turn(monkeypatch, tmp_path) -> None:
    """The bug that shipped: the pool evicts, a new client is built counting from
    zero, and the ledger's memory of the dead one clamps the turn to $0. This is
    that exact sequence, end to end, through the real seam."""
    engine = await _wired(monkeypatch, tmp_path, [0.028, 0.030, 0.033])
    await _run(engine, "one")
    await _run(engine, "two")
    await engine.pool.close_one("canary/s1")  # LRU/idle eviction — NOT _retire

    import aire.engine.core as core
    monkeypatch.setattr(core, "ClaudeSDKClient", lambda options=None: FakeClient([0.025]))
    await _run(engine, "after the eviction")

    rows = await _rows()
    assert len(rows) == 3, "the turn after an eviction banked nothing"
    assert float(rows[-1]["usd"]) == pytest.approx(0.025)
