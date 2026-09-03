"""Gateway-ported /invite endpoint — auth, fail-closed, routing.

This is the port of personas.alice.api.server onto the persona gateway so ALICE
runs on ONE host (kills the double-reply "metiche") and the legacy alice-bot can
be retired. Mutator/contract rule: positive (valid token + ready persona → 202
schedules dispatch_invite with the right args) + resistance (no token / bad
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
    """A booted persona client: .user is set, dispatch_invite is awaitable."""
    return SimpleNamespace(user=SimpleNamespace(id=1503983124982534284), dispatch_invite=AsyncMock())


def test_invite_happy_path_schedules_with_args():
    client = _ready_client()
    app = build_invite_app({INVITE_PERSONA_ID: client}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 202
    assert r.json() == {"status": "invited", "channel_id": PAYLOAD["channel_id"], "detail": None}
    client.dispatch_invite.assert_called_once()
    kwargs = client.dispatch_invite.call_args.kwargs
    assert kwargs["channel_id"] == PAYLOAD["channel_id"]
    assert kwargs["reason"] == PAYLOAD["reason"]
    assert kwargs["invited_by"] == "insult_rest"
    assert kwargs["trigger_message_id"] is None


def test_invite_forwards_trigger_message_id():
    """The wire carries the summoning message id so the persona's [REACT:]
    markers land on it instead of being dropped (2026-07-14 Vultur bug)."""
    client = _ready_client()
    app = build_invite_app({INVITE_PERSONA_ID: client}, TOKEN)
    payload = {**PAYLOAD, "trigger_message_id": "1526655478313127987"}
    with TestClient(app) as http:
        r = http.post("/invite", json=payload, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 202
    kwargs = client.dispatch_invite.call_args.kwargs
    assert kwargs["trigger_message_id"] == "1526655478313127987"


def test_invite_missing_token_is_401():
    client = _ready_client()
    app = build_invite_app({INVITE_PERSONA_ID: client}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD)
    assert r.status_code == 401
    client.dispatch_invite.assert_not_called()


def test_invite_bad_token_is_401():
    client = _ready_client()
    app = build_invite_app({INVITE_PERSONA_ID: client}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD, headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401
    client.dispatch_invite.assert_not_called()


def test_invite_unconfigured_token_is_503():
    # RESISTANCE: gateway booted without GATEWAY_INVITE_TOKEN → fail closed.
    client = _ready_client()
    app = build_invite_app({INVITE_PERSONA_ID: client}, "")
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD, headers={"Authorization": "Bearer anything"})
    assert r.status_code == 503
    client.dispatch_invite.assert_not_called()


def test_invite_persona_not_registered_is_503():
    # RESISTANCE: alice persona has no token/never started → not in registry.
    app = build_invite_app({}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 503


def test_invite_persona_not_ready_is_503():
    # RESISTANCE: persona registered but pre-on_ready (user is None) → 503, no schedule.
    client = SimpleNamespace(user=None, dispatch_invite=AsyncMock())
    app = build_invite_app({INVITE_PERSONA_ID: client}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 503
    client.dispatch_invite.assert_not_called()


def test_health_is_public():
    app = build_invite_app({}, TOKEN)
    with TestClient(app) as http:
        r = http.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_invite_persona_id_routes_to_that_persona():
    # HOST 5/6 slice C: the LLM router cutover summons vultur/frugivoro through
    # the SAME endpoint via the optional persona_id field.
    alice = _ready_client()
    vultur = _ready_client()
    app = build_invite_app({INVITE_PERSONA_ID: alice, "vultur": vultur}, TOKEN)
    payload = {**PAYLOAD, "persona_id": "vultur", "invited_by": "host_router"}
    with TestClient(app) as http:
        r = http.post("/invite", json=payload, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 202
    vultur.dispatch_invite.assert_called_once()
    alice.dispatch_invite.assert_not_called()
    kwargs = vultur.dispatch_invite.call_args.kwargs
    assert kwargs["invited_by"] == "host_router"


def test_invite_omitted_persona_id_keeps_alice_wire_contract():
    # RESISTANCE: the legacy caller sends no persona_id — alice answers, exactly
    # as before the field existed.
    alice = _ready_client()
    vultur = _ready_client()
    app = build_invite_app({INVITE_PERSONA_ID: alice, "vultur": vultur}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 202
    alice.dispatch_invite.assert_called_once()
    vultur.dispatch_invite.assert_not_called()
    assert alice.dispatch_invite.call_args.kwargs["invited_by"] == "insult_rest"


def test_invite_explicit_unknown_persona_is_400():
    # RESISTANCE: an explicitly-requested persona the gateway doesn't host is a
    # caller bug (400), never a silent alice fallback and never a retryable 503.
    alice = _ready_client()
    app = build_invite_app({INVITE_PERSONA_ID: alice}, TOKEN)
    payload = {**PAYLOAD, "persona_id": "gandalf"}
    with TestClient(app) as http:
        r = http.post("/invite", json=payload, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 400
    alice.dispatch_invite.assert_not_called()


# --- wait: the caller owns the outcome (2026-09-03) ---------------------------


def _client_with_outcome(outcome: str) -> SimpleNamespace:
    return SimpleNamespace(
        user=SimpleNamespace(id=1503983124982534284), dispatch_invite=AsyncMock(return_value=outcome)
    )


def test_wait_reports_delivered_with_200_and_no_gateway_fallback():
    """`wait: true` awaits the turn and answers with what happened — the 202 at
    scheduling time told the host nothing, so the persona was left to mumble
    "…" on its own. The waiting caller owns the failure: `fallback=False`."""
    client = _client_with_outcome("delivered")
    app = build_invite_app({INVITE_PERSONA_ID: client}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json={**PAYLOAD, "wait": True}, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert r.json()["status"] == "delivered"
    assert client.dispatch_invite.call_args.kwargs["fallback"] is False


def test_wait_reports_failed_with_502():
    client = _client_with_outcome("failed")
    app = build_invite_app({INVITE_PERSONA_ID: client}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json={**PAYLOAD, "wait": True}, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 502
    assert r.json()["status"] == "failed"


def test_without_wait_the_202_contract_is_untouched():
    """Fire-and-forget callers keep the gateway-owned "…" (fallback default True)."""
    client = _ready_client()
    app = build_invite_app({INVITE_PERSONA_ID: client}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 202
    assert "fallback" not in client.dispatch_invite.call_args.kwargs
