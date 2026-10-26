"""The ceiling route (#51): the owner's token moves one live key's limit, every
door token is turned away, and the key's spend history survives the move.
Over a real socket like the sibling doors, with the database played by a fake
connection that records the UPDATE it was handed."""

import asyncio
import os
from types import SimpleNamespace

import httpx
import pytest

from aire import bearer, ceiling, db, door, tokens
from test_gateway import _serve

OWNER, CANARY = "owner-tok-1", "canary-tok-1"


@pytest.fixture(scope="module")
def gate():
    from aire.server import app
    url, server = _serve(app)
    yield url
    server.should_exit = True


@pytest.fixture
def wired(monkeypatch):
    monkeypatch.setenv("AIRE_AUTH_TOKEN", OWNER)
    monkeypatch.setenv("AIRE_CANARY_TOKEN", CANARY)
    monkeypatch.setattr(bearer, "ACCEPTED_TOKENS", (OWNER, CANARY))
    monkeypatch.setattr(door, "ACCEPTED_TOKENS", (OWNER, CANARY))
    rows = {"visalaw-judge": {"nickname": "visalaw-judge", "budget_usd": 0.05, "spent_usd": 0.0001}}
    updates = []

    class Conn:
        async def execute(self, *_):
            return None

        async def fetchrow(self, _sql, nickname, budget):
            updates.append((nickname, budget))
            row = rows.get(nickname)
            if row is None:
                return None
            row["budget_usd"] = budget
            return row

    class Acquire:
        async def __aenter__(self):
            return Conn()

        async def __aexit__(self, *_):
            return False

    async def reload():
        tokens._by_hash.clear()
        for row in rows.values():
            tokens._by_hash[tokens.digest(f"key-{row['nickname']}")] = tokens.Holder(
                row["nickname"], row["budget_usd"], row["spent_usd"])

    monkeypatch.setattr(db, "acquire", lambda *a, **k: Acquire())
    monkeypatch.setattr(tokens, "load", reload)
    asyncio.run(reload())
    return SimpleNamespace(updates=updates, rows=rows)


def _post(url, body, token):
    async def go():
        async with httpx.AsyncClient(timeout=10) as client:
            return await client.post(f"{url}/access/ceiling", json=body,
                                     headers={"authorization": f"Bearer {token}"})
    return asyncio.run(go())


def test_the_canary_is_a_door_token_not_the_owner(gate, wired):
    r = _post(gate, {"nickname": "visalaw-judge", "budget_usd": 5.0}, CANARY)
    assert r.status_code == 401
    assert wired.updates == []


def test_a_wrong_token_is_refused_before_the_database(gate, wired):
    r = _post(gate, {"nickname": "visalaw-judge", "budget_usd": 5.0}, "not-the-owner")
    assert r.status_code == 401
    assert wired.updates == []


def test_no_owner_token_configured_means_nobody_is_the_owner(gate, wired, monkeypatch):
    monkeypatch.setenv("AIRE_AUTH_TOKEN", "")
    r = _post(gate, {"nickname": "visalaw-judge", "budget_usd": 5.0}, OWNER)
    assert r.status_code == 401
    assert wired.updates == []


@pytest.mark.parametrize("body", [{"nickname": "", "budget_usd": 5.0},
                                  {"nickname": "visalaw-judge", "budget_usd": 0},
                                  {"nickname": "visalaw-judge", "budget_usd": "inf"},
                                  {"nickname": "visalaw-judge"}])
def test_a_bad_body_is_a_400_and_touches_nothing(gate, wired, body):
    r = _post(gate, body, OWNER)
    assert r.status_code == 400
    assert wired.updates == []


def test_an_unknown_or_revoked_nickname_is_a_404(gate, wired):
    r = _post(gate, {"nickname": "nobody", "budget_usd": 5.0}, OWNER)
    assert r.status_code == 404
    assert wired.updates == [("nobody", 5.0)]


def test_the_owner_moves_the_ceiling_and_the_spend_survives(gate, wired):
    r = _post(gate, {"nickname": "visalaw-judge", "budget_usd": 5.0}, OWNER)
    assert r.status_code == 200
    assert r.json() == {"nickname": "visalaw-judge", "budget_usd": 5.0, "spent_usd": 0.0001}
    assert wired.updates == [("visalaw-judge", 5.0)]
    holder = tokens.identify("key-visalaw-judge")
    assert holder is not None and holder.budget_usd == 5.0 and holder.spent_usd == 0.0001
    assert not holder.exhausted()


def test_is_owner_compares_the_whole_token():
    os.environ["AIRE_AUTH_TOKEN"] = "abcdef"
    try:
        assert ceiling._is_owner("abcdef")
        assert not ceiling._is_owner("abcde")
        assert not ceiling._is_owner("abcdefg")
        assert not ceiling._is_owner("")
    finally:
        os.environ.pop("AIRE_AUTH_TOKEN")
