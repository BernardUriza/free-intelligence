"""`/invite` con boleto — el turno del gateway detrás de requests cortas.

Positiva: `wait + ticket` contesta 202 con `turn_id` al instante, un poll corto
dice `running`, y el poll posterior entrega el outcome real del turno
(`delivered`) — sin que ninguna request haya durado lo que duró el turno. Es la
mitad host↔gateway del 2026-09-19. Resistencia: un `wait` sin `ticket` sigue
siendo síncrono (un gateway nuevo no cambia el contrato de un host viejo), un
`turn_id` desconocido es 404, y el poll exige el mismo bearer que `/invite`.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient

from persona_gateway.invite_server import INVITE_PERSONA_ID, build_invite_app

TOKEN = "s3cr3t-token"  # noqa: S105 — fixture, no un secreto
AUTH = {"Authorization": f"Bearer {TOKEN}"}
PAYLOAD = {
    "channel_id": "1489180895264116736",
    "guild_id": "1488419218302042223",
    "channel_name": "general",
    "reason": "Bernard pidió la trayectoria de Supremme de Luxe.",
    "persona_id": INVITE_PERSONA_ID,
    "wait": True,
    "ticket": True,
}


def _client_with_turn(delay_s: float, outcome: str = "delivered") -> SimpleNamespace:
    async def dispatch_invite(**_kw) -> str:
        await asyncio.sleep(delay_s)
        return outcome

    return SimpleNamespace(user=SimpleNamespace(id=1), dispatch_invite=dispatch_invite)


def test_ticket_mode_answers_at_once_and_the_poll_delivers_the_outcome():
    app = build_invite_app({INVITE_PERSONA_ID: _client_with_turn(0.2)}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json=PAYLOAD, headers=AUTH)
        assert r.status_code == 202
        body = r.json()
        assert body["status"] == "running"
        turn_id = body["turn_id"]
        assert turn_id

        r = http.get(f"/invite/turns/{turn_id}", params={"wait_s": 0.01}, headers=AUTH)
        assert r.status_code == 200 and r.json()["status"] == "running"

        r = http.get(f"/invite/turns/{turn_id}", params={"wait_s": 5}, headers=AUTH)
        assert r.status_code == 200
        assert r.json() == {
            "status": "delivered",
            "channel_id": PAYLOAD["channel_id"],
            "detail": None,
            "turn_id": turn_id,
        }

        # Recogido = borrado: el mismo id ya es la señal de "reinicio".
        assert http.get(f"/invite/turns/{turn_id}", headers=AUTH).status_code == 404


def test_a_failed_turn_travels_as_a_200_with_status_failed():
    app = build_invite_app({INVITE_PERSONA_ID: _client_with_turn(0.0, "failed")}, TOKEN)
    with TestClient(app) as http:
        turn_id = http.post("/invite", json=PAYLOAD, headers=AUTH).json()["turn_id"]
        r = http.get(f"/invite/turns/{turn_id}", params={"wait_s": 5}, headers=AUTH)
    assert r.status_code == 200 and r.json()["status"] == "failed"


def test_wait_without_ticket_is_still_the_synchronous_contract():
    app = build_invite_app({INVITE_PERSONA_ID: _client_with_turn(0.0)}, TOKEN)
    with TestClient(app) as http:
        r = http.post("/invite", json={**PAYLOAD, "ticket": False}, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["status"] == "delivered" and r.json()["turn_id"] is None


def test_unknown_turn_is_404_and_the_poll_needs_the_bearer():
    app = build_invite_app({INVITE_PERSONA_ID: _client_with_turn(0.0)}, TOKEN)
    with TestClient(app) as http:
        assert http.get("/invite/turns/deadbeef", headers=AUTH).status_code == 404
        assert http.get("/invite/turns/deadbeef").status_code == 401
        assert http.get("/invite/turns/deadbeef", headers={"Authorization": "Bearer wrong"}).status_code == 401
