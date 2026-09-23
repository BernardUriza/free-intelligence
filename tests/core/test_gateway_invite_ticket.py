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


# --- boleto durable (2026-09-23): el gateway reiniciado contesta desde su fila -----

from unittest.mock import AsyncMock  # noqa: E402

from tests.shared.fake_ledger import FakeInviteMemory  # noqa: E402

HOST_ID = "c0ffee00c0ffee00c0ffee00c0ffee00"


def _recording_client(outcome: str = "delivered", delay_s: float = 0.0):
    calls: list[dict] = []

    async def dispatch_invite(**kw) -> str:
        calls.append(kw)
        await asyncio.sleep(delay_s)
        return outcome

    return SimpleNamespace(user=SimpleNamespace(id=1), dispatch_invite=dispatch_invite), calls


def test_the_hosts_turn_id_is_honoured_and_a_repeat_is_one_dispatch():
    memory = FakeInviteMemory()
    client, calls = _recording_client(delay_s=0.2)
    app = build_invite_app({INVITE_PERSONA_ID: client}, TOKEN, memory=memory)
    with TestClient(app) as http:
        first = http.post("/invite", json={**PAYLOAD, "turn_id": HOST_ID}, headers=AUTH)
        second = http.post("/invite", json={**PAYLOAD, "turn_id": HOST_ID}, headers=AUTH)
        assert first.json()["turn_id"] == second.json()["turn_id"] == HOST_ID
        r = http.get(f"/invite/turns/{HOST_ID}", params={"wait_s": 5}, headers=AUTH)
    assert r.json()["status"] == "delivered"
    assert len(calls) == 1 and calls[0]["turn_id"] == HOST_ID and calls[0]["resume_from"] is None
    assert memory.ledger.rows[HOST_ID]["status"] == "done" and memory.ledger.rows[HOST_ID]["stage"] == "delivered"


def test_after_a_restart_a_delivered_row_answers_delivered_and_dispatches_nothing():
    memory = FakeInviteMemory()
    client, _calls = _recording_client()
    with TestClient(build_invite_app({INVITE_PERSONA_ID: client}, TOKEN, memory=memory)) as http:
        http.post("/invite", json={**PAYLOAD, "turn_id": HOST_ID}, headers=AUTH)
        assert http.get(f"/invite/turns/{HOST_ID}", params={"wait_s": 5}, headers=AUTH).json()["status"] == "delivered"
    # Réplica nueva: otro registro (otro proceso), el mismo ledger.
    client2, calls2 = _recording_client()
    with TestClient(build_invite_app({INVITE_PERSONA_ID: client2}, TOKEN, memory=memory)) as http:
        poll = http.get(f"/invite/turns/{HOST_ID}", params={"wait_s": 1}, headers=AUTH)
        repost = http.post("/invite", json={**PAYLOAD, "turn_id": HOST_ID}, headers=AUTH)
    assert poll.status_code == 200 and poll.json()["status"] == "delivered"
    assert repost.status_code == 200 and repost.json()["status"] == "delivered"
    assert calls2 == []


def test_an_orphaned_row_is_resumed_in_its_stage_under_the_same_turn_id():
    memory = FakeInviteMemory()
    memory.ledger.seed(
        HOST_ID, payload={**PAYLOAD, "persona_id": INVITE_PERSONA_ID}, stage="runner_done", stage_text="hola"
    )
    client, calls = _recording_client()
    with TestClient(build_invite_app({INVITE_PERSONA_ID: client}, TOKEN, memory=memory)) as http:
        r = http.get(f"/invite/turns/{HOST_ID}", params={"wait_s": 5}, headers=AUTH)
    assert r.json()["status"] == "delivered"
    assert len(calls) == 1 and calls[0]["turn_id"] == HOST_ID
    assert calls[0]["resume_from"].extra["stage"] == "runner_done" and calls[0]["resume_from"].attempts == 2


def test_a_row_another_replica_still_beats_is_not_dispatched_again():
    memory = FakeInviteMemory()
    memory.ledger.seed(HOST_ID, payload={**PAYLOAD, "persona_id": INVITE_PERSONA_ID}, stale=False)
    client, calls = _recording_client()
    with TestClient(build_invite_app({INVITE_PERSONA_ID: client}, TOKEN, memory=memory)) as http:
        r = http.get(f"/invite/turns/{HOST_ID}", params={"wait_s": 0.01}, headers=AUTH)
    assert r.json()["status"] == "running" and calls == []


def test_a_second_resume_is_refused_as_failed_so_the_host_retries_with_a_new_id():
    memory = FakeInviteMemory()
    memory.ledger.seed(HOST_ID, payload={**PAYLOAD, "persona_id": INVITE_PERSONA_ID}, attempts=2)
    client, calls = _recording_client()
    with TestClient(build_invite_app({INVITE_PERSONA_ID: client}, TOKEN, memory=memory)) as http:
        r = http.get(f"/invite/turns/{HOST_ID}", params={"wait_s": 0.01}, headers=AUTH)
    assert r.json()["status"] == "failed" and calls == []


def test_boot_resume_claims_the_orphans_nobody_is_polling():
    memory = FakeInviteMemory()
    memory.ledger.seed(
        HOST_ID, payload={**PAYLOAD, "persona_id": INVITE_PERSONA_ID}, stage="markers_done", stage_text="x"
    )
    client, calls = _recording_client()
    app = build_invite_app({INVITE_PERSONA_ID: client}, TOKEN, memory=memory)
    with TestClient(app) as http:
        assert http.portal.call(app.state.resume_stale_turns) == 1
        r = http.get(f"/invite/turns/{HOST_ID}", params={"wait_s": 5}, headers=AUTH)
    assert r.json()["status"] == "delivered" and len(calls) == 1


def test_with_the_ledger_down_the_contract_is_exactly_ram_only():
    memory = FakeInviteMemory()
    memory.ledger.fail = True
    client, calls = _recording_client()
    with TestClient(build_invite_app({INVITE_PERSONA_ID: client}, TOKEN, memory=memory)) as http:
        turn_id = http.post("/invite", json=PAYLOAD, headers=AUTH).json()["turn_id"]
        assert http.get(f"/invite/turns/{turn_id}", params={"wait_s": 5}, headers=AUTH).json()["status"] == "delivered"
        assert http.get(f"/invite/turns/{turn_id}", headers=AUTH).status_code == 404
    assert len(calls) == 1 and memory.ledger.rows == {}


def test_the_shutdown_controller_releases_open_tickets():
    from persona_gateway.app import ShutdownController
    from persona_gateway.drain import TurnGate

    controller = ShutdownController(TurnGate(), {}, timeout_s=0.01)
    controller.turn_tickets = SimpleNamespace(release_open=AsyncMock(return_value=1))
    asyncio.run(controller.run())
    controller.turn_tickets.release_open.assert_awaited_once()
