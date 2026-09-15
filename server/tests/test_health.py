"""What /health tells whom (backlog #40).

Two things must both hold and they pull against each other: an operator has to
be able to see which guards are silently off — that is the whole point of
`arming.py` — and this endpoint is the ONE route the door lets through with no
token at all, so the same list must not be readable from the internet. A list of
which defences are currently down is reconnaissance, not health.
"""

import os

import pytest
from fastapi.testclient import TestClient

TOKEN = "the-owners-own-door-token"


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("AIRE_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("AIRE_MAX_SPEND_USD", "20")
    monkeypatch.delenv("AIRE_VERB_TOKEN", raising=False)
    import aire.bearer

    monkeypatch.setattr(aire.bearer, "ACCEPTED_TOKENS", (TOKEN,))
    from aire.server import app

    return TestClient(app, raise_server_exceptions=False)


def test_an_anonymous_caller_learns_nothing_about_the_guards(client):
    body = client.get("/health").json()
    assert body["status"] in ("ok", "degraded")
    assert "armed" not in body and "disarmed" not in body, \
        "the internet must not read which defences are down"
    assert "credential_slots" not in body


def test_the_owner_sees_every_guard_and_which_are_off(client):
    body = client.get("/health", headers={"authorization": f"Bearer {TOKEN}"}).json()
    assert body["armed"]["spend_backstop"] is True, "the env var is set in this fixture"
    assert body["armed"]["verbs"] is False, "and this one deliberately is not"
    assert "verbs" in body["disarmed"]
    assert body["door_tokens"] == 1


def test_the_owner_sees_the_credential_chain_by_slot_not_just_a_count(client):
    """The count hid which slot was empty. The armed slots are named so an
    empty `oauth-backup` is visible, and the live rotor state rides beside the
    config so costwatch can alarm when every slot is dry (2026-09-15)."""
    body = client.get("/health", headers={"authorization": f"Bearer {TOKEN}"}).json()
    assert isinstance(body["credential_slots_armed"], list)
    assert "credentials_all_dry" in body
    assert "credentials_cooling" in body


def test_the_credential_chain_is_never_readable_anonymously(client):
    body = client.get("/health").json()
    assert "credential_slots_armed" not in body
    assert "credentials_all_dry" not in body


def test_a_wrong_token_is_treated_as_anonymous_not_as_an_error(client):
    body = client.get("/health", headers={"authorization": "Bearer nope"}).json()
    assert body["status"] in ("ok", "degraded")
    assert "disarmed" not in body


def test_the_report_carries_no_secret_value(client):
    """It reports STATE, never values — a count of slots, never a token. A
    monitoring surface that leaks the thing it monitors is worse than none."""
    os.environ["AIRE_VERB_TOKEN"] = "s3cr3t-verb-token"
    try:
        raw = client.get("/health", headers={"authorization": f"Bearer {TOKEN}"}).text
    finally:
        del os.environ["AIRE_VERB_TOKEN"]
    assert "s3cr3t-verb-token" not in raw and TOKEN not in raw
