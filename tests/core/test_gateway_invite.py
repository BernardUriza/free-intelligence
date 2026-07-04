"""Gateway-ported /invite endpoint — auth, fail-closed, routing.

This is the port of personas.alice.api.server onto the persona gateway so ALICE
runs on ONE host (kills the double-reply "metiche") and the legacy alice-bot can
be retired. Mutator/contract rule: positive (valid token + ready persona → 202
schedules respond_to_invite with the right args) + resistance (no token / bad
token / unconfigured / persona-not-ready all refuse, never schedule).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from persona_gateway.invite_server import INVITE_PERSONA_ID, build_invite_app

TOKEN = "s3cr3t-token"  # noqa: S105 — fixture token, not a real secret
PAYLOAD = {
    "channel_id": "1489180895264116736",
    "guild_id": "1488419218302042223",
    "channel_name": "general",
    "reason": "Bernard is going sharp on Alex's silence; need an empathic mirror.",
}


def _ready_client() -> SimpleNamespace:
    """A booted persona client: .user is set, respond_to_invite is awaitable."""
    return SimpleNamespace(user=SimpleNamespace(id=1503983124982534284), respond_to_invite=AsyncMock())


def test_invite_happy_path_schedules_with_args():
    client = _ready_client()
    app = build_invite_app({INVITE_PERSONA_ID: client}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 202
    assert r.json() == {"status": "invited", "channel_id": PAYLOAD["channel_id"], "detail": None}
    client.respond_to_invite.assert_called_once()
    kwargs = client.respond_to_invite.call_args.kwargs
    assert kwargs["channel_id"] == PAYLOAD["channel_id"]
    assert kwargs["reason"] == PAYLOAD["reason"]
    assert kwargs["invited_by"] == "insult_rest"


def test_invite_missing_token_is_401():
    client = _ready_client()
    app = build_invite_app({INVITE_PERSONA_ID: client}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD)
    assert r.status_code == 401
    client.respond_to_invite.assert_not_called()


def test_invite_bad_token_is_401():
    client = _ready_client()
    app = build_invite_app({INVITE_PERSONA_ID: client}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD, headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401
    client.respond_to_invite.assert_not_called()


def test_invite_unconfigured_token_is_503():
    # RESISTANCE: gateway booted without INSULT_TO_ALICE_TOKEN → fail closed.
    client = _ready_client()
    app = build_invite_app({INVITE_PERSONA_ID: client}, "")
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD, headers={"Authorization": "Bearer anything"})
    assert r.status_code == 503
    client.respond_to_invite.assert_not_called()


def test_invite_persona_not_registered_is_503():
    # RESISTANCE: alice persona has no token/never started → not in registry.
    app = build_invite_app({}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 503


def test_invite_persona_not_ready_is_503():
    # RESISTANCE: persona registered but pre-on_ready (user is None) → 503, no schedule.
    client = SimpleNamespace(user=None, respond_to_invite=AsyncMock())
    app = build_invite_app({INVITE_PERSONA_ID: client}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 503
    client.respond_to_invite.assert_not_called()


def test_health_is_public():
    app = build_invite_app({}, TOKEN)
    with TestClient(app) as http:
        r = http.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
