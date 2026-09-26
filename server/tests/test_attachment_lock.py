"""The session-weight check that cannot be raced (#50, adversarial finding 7).

The door weighs a session BEFORE the turn, so two concurrent turns on one
session could both pass it. The authoritative check runs in `turn._serve`,
under the lock that serializes the session's turns: the second turn waits for
the first to land in the store, then is weighed WITH it. This drives the real
`run_turn` against a fake SDK client whose `query` "lands" the attachments in a
fake store, so the race is real and only the subprocess is not."""

import asyncio
from typing import Any

import pytest

from aire.engine import attachment_budget, turn
from aire.engine.contract import TurnSpec
from aire.engine.core import Engine

IMG = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "x"}}
STORE = {"images": 0}


class Block:
    text = "ok"


class AssistantMessage:
    content = [Block()]
    model = "m"


class ResultMessage:
    usage = {"input_tokens": 1, "output_tokens": 1}
    total_cost_usd = 0.0
    session_id = "s"


class FakeClient:
    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *_: Any) -> bool:
        return False

    async def query(self, payload: Any) -> None:
        async for message in payload:
            await asyncio.sleep(0.05)  # the turn takes time; the other request is waiting
            STORE["images"] += sum(1 for b in message["message"]["content"] if b["type"] == "image")

    async def receive_response(self) -> Any:
        yield AssistantMessage()
        yield ResultMessage()


class Slot:
    name = "primary"
    env: dict = {}


class Rotor:
    def active(self) -> Slot:
        return Slot()


class NoMemory:
    async def load(self, *_: Any, **__: Any) -> list:
        return []


@pytest.mark.asyncio
async def test_the_second_of_two_racing_turns_is_weighed_with_the_first(monkeypatch, tmp_path):
    import aire.engine.core as core

    async def held(*_):
        return STORE["images"], 0

    async def bank(*_a, **_k):
        return None
    STORE["images"] = 0
    monkeypatch.setattr(core, "WORKSPACES", tmp_path)
    monkeypatch.setattr(core, "build_options", lambda *a, **k: None)
    monkeypatch.setattr(core, "SDKClient", lambda provider="claude", *, options=None: FakeClient())
    monkeypatch.setattr(attachment_budget, "held", held)
    monkeypatch.setattr(turn.spend, "bank", bank)
    engine = Engine(NoMemory())
    engine.rotor = Rotor()
    batch = (IMG,) * 60  # each fits alone (100 cap); together they do not

    async def one() -> list[dict]:
        return [e async for e in turn.run_turn(engine, "p", "s", "mira", TurnSpec(mode="complete"), batch)]

    first, second = await asyncio.gather(one(), one())
    outcomes = sorted(["result" in [e["type"] for e in ev] for ev in (first, second)])
    assert outcomes == [False, True]
    refused = first if not any(e["type"] == "result" for e in first) else second
    assert refused[0]["error"] == "attachment_budget" and "60 images" in refused[0]["detail"]
    assert STORE["images"] == 60
