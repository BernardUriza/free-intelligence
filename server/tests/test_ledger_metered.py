"""The spend ceiling guards the CARD, not the subscription (the 2026-08-25 P1).

For 16 hours every persona riding the engine was mute: the RAM ledger had
banked $20 of NOMINAL OAuth spend — dollars the Max subscription had already
paid — and `run_stream` refused every turn until a restart zeroed it. The cure
is semantic, not a bigger number: only a METERED slot's dollars move the
ceiling, and the ceiling refuses only turns that would ride a metered slot.

Three pins: the arithmetic (an OAuth delta is recorded but not banked), the
gate's direction (an exhausted ledger still serves OAuth turns), and the gate's
teeth (the same exhausted ledger still refuses the metered slot).
"""

from typing import Any

import pytest

import aire.engine.ledger as ledger_mod
from aire.engine.contract import BudgetExceeded, TurnSpec
from aire.engine.core import Engine
from aire.engine.credentials import is_metered
from aire.engine.ledger import Ledger
from aire.engine.turn import run_turn


def test_the_chain_knows_which_slots_bill_the_card() -> None:
    assert not is_metered("oauth-primary")
    assert not is_metered("oauth-backup")
    assert is_metered("api-key-fallback")
    assert is_metered("ambient"), "an unknown credential counts as real money"


def test_oauth_spend_returns_its_delta_but_never_moves_the_ceiling() -> None:
    ledger, key = Ledger(), "canary/s1"
    delta, _ = ledger.account(key, 0.50, metered=False)
    assert delta == pytest.approx(0.50), "the monthly record still needs the delta"
    assert ledger.spend_usd == 0.0, "nominal dollars moved the card ceiling"

    delta, _ = ledger.account("canary/s2", 0.25, metered=True)
    assert delta == pytest.approx(0.25)
    assert ledger.spend_usd == pytest.approx(0.25), "real dollars must still count"


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
        self.usage = {"input_tokens": 10, "output_tokens": 42}
        self.total_cost_usd = cumulative
        self.session_id = "0ad1b2c3-0000-5000-8000-000000000001"


class _FakeClient:
    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *_: Any) -> bool:
        return False

    async def query(self, _payload: Any) -> None:
        return None

    async def receive_response(self) -> Any:
        yield AssistantMessage("PONG")
        yield ResultMessage(0.028)


class _Slot:
    env: dict = {}

    def __init__(self, name: str) -> None:
        self.name = name


class _Rotor:
    def __init__(self, name: str) -> None:
        self._name = name

    def active(self) -> _Slot:
        return _Slot(self._name)

    def burn(self, _name: str) -> None:
        raise AssertionError("a healthy turn must not burn a credential slot")


class _NoMemory:
    async def load(self, *_: Any, **__: Any) -> list:
        return []


async def _wired(monkeypatch, tmp_path, slot_name: str) -> Engine:
    import aire.engine.core as core
    import aire.engine.turn as turn_mod

    monkeypatch.setattr(core, "WORKSPACES", tmp_path)
    monkeypatch.setattr(core, "build_options", lambda *a, **k: None)
    monkeypatch.setattr(core, "ClaudeSDKClient", lambda options=None: _FakeClient())

    async def _no_bank(*_a: Any, **_k: Any) -> None:
        return None

    monkeypatch.setattr(turn_mod.spend, "bank", _no_bank)
    engine = Engine(_NoMemory())
    engine.rotor = _Rotor(slot_name)
    return engine


@pytest.mark.asyncio
async def test_an_exhausted_ledger_still_serves_the_oauth_slot(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ledger_mod, "MAX_SPEND_USD", 20.0)
    engine = await _wired(monkeypatch, tmp_path, "oauth-primary")
    engine.ledger.spend_usd = 20.45  # the founding incident's exact reading

    events = [ev async for ev in
              run_turn(engine, "canary", "s1", "hi", TurnSpec(mode="complete"))]
    assert [e["type"] for e in events] == ["text", "result"], \
        "a subscription turn was refused to protect money nobody was billed"


@pytest.mark.asyncio
async def test_the_same_exhausted_ledger_still_refuses_the_metered_slot(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ledger_mod, "MAX_SPEND_USD", 20.0)
    engine = await _wired(monkeypatch, tmp_path, "api-key-fallback")
    engine.ledger.spend_usd = 20.45

    with pytest.raises(BudgetExceeded):
        async for _ in run_turn(engine, "canary", "s1", "hi", TurnSpec(mode="complete")):
            pass
