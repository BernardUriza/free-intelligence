"""An invited key pays METERED dollars only, and only the turn's delta (#54).

The Stop judge's key (5 USD ceiling) runs on a Codex plan seat: every turn
reports ~0.066 nominal dollars nobody is billed. The door banked that whole
`total_cost_usd` — the client's CUMULATIVE spend, at that — so the key would
402 within ~75 verdicts on money that never left a card. The engine now stamps
each `result` with `metered` and `billed_usd`, and the door banks only that.
"""

from typing import Any

import pytest

from aire import messages, tokens
from aire.engine.contract import TurnSpec
from aire.engine.detach import drain_detached
from aire.engine.turn import run_turn
from test_ledger_metered import _wired

HOLDER = tokens.Holder("personal-stop-judge", 5.0, 0.0)


async def _result(engine: Any) -> dict[str, Any]:
    events = [ev async for ev in run_turn(engine, "stop-judge", "d1", "claim", TurnSpec(mode="complete"))]
    return next(ev for ev in events if ev["type"] == "result")


@pytest.mark.asyncio
async def test_a_plan_seat_result_owes_nothing(monkeypatch, tmp_path) -> None:
    engine = await _wired(monkeypatch, tmp_path, "codex/oauth/primary", cumulative=0.066)
    ev = await _result(engine)
    assert ev["metered"] is False
    assert ev["billed_usd"] == 0.0, "a plan seat's nominal dollars reached the invite ceiling"


@pytest.mark.asyncio
async def test_a_metered_result_owes_its_delta(monkeypatch, tmp_path) -> None:
    engine = await _wired(monkeypatch, tmp_path, "codex/apikey/fallback", cumulative=0.066)
    first = await _result(engine)
    second = await _result(engine)
    assert (first["metered"], first["billed_usd"]) == (True, pytest.approx(0.066))
    assert second["billed_usd"] == 0.0, "the cumulative total was billed again"


def _charges(monkeypatch) -> list[tuple[str, float]]:
    charged: list[tuple[str, float]] = []

    async def charge(nickname: str, usd: float) -> None:
        charged.append((nickname, usd))

    monkeypatch.setattr(tokens, "charge", charge)
    return charged


@pytest.mark.asyncio
async def test_the_door_charges_no_plan_seat_turn(monkeypatch, capsys) -> None:
    charged = _charges(monkeypatch)
    await messages._bank(HOLDER, {"type": "result", "metered": False, "billed_usd": 0.0})
    assert charged == []
    assert "plan-seat turn, nothing billed" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_the_door_charges_the_metered_delta(monkeypatch) -> None:
    charged = _charges(monkeypatch)
    await messages._bank(HOLDER, {"type": "result", "metered": True, "billed_usd": 0.004})
    assert charged == [("personal-stop-judge", 0.004)]


@pytest.mark.asyncio
async def test_an_unstamped_result_still_says_the_ceiling_is_not_biting(monkeypatch, capsys) -> None:
    charged = _charges(monkeypatch)
    await messages._bank(HOLDER, {"type": "result"})
    assert charged == [("personal-stop-judge", 0.0)]
    assert "the ceiling is not biting" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_a_detached_turn_hands_the_stamped_result_to_its_sink() -> None:
    seen: list[dict[str, Any]] = []

    async def events() -> Any:
        yield {"type": "text", "text": "PASS"}
        yield {"type": "result", "metered": False, "billed_usd": 0.0}

    async def sink(ev: dict[str, Any]) -> None:
        seen.append(ev)

    await drain_detached(events(), "stop-judge/d1", sink)
    assert seen == [{"type": "result", "metered": False, "billed_usd": 0.0}]
