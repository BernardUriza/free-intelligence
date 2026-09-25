"""`/v1/turn/jobs` — el turno del runner con boleto.

Positiva: el alta devuelve 202 + job_id, un poll corto dice `running`, y el poll
que llega después de que AIRE terminó entrega el TurnResponse íntegro. Es el
caso del 2026-09-19: 326.9 s de turno, entregado, y sin nadie escuchando.
Resistencia: un id desconocido es 404 (la señal de "el runner se reinició"),
sin token es 401 igual que el camino síncrono, y un turno que revienta sale con
la misma excepción que en `/v1/turn`.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from persona_runner.api import turn as turn_api
from persona_runner.core.schemas import TurnRequest, TurnResponse
from persona_runner.engine import turn_jobs

TOKEN = "tok-1"  # noqa: S105 — fixture, no un secreto
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
REQ = {
    "channel_id": "1489180895264116736",
    "user_id": "907264175246569543",
    "user_text": "hola",
    "persona_id": "vultur",
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("persona_runner.core.config.RUNNER_AUTH_TOKEN", TOKEN)
    turn_jobs.JOBS.clear()
    app = FastAPI()
    app.include_router(turn_api.router)
    with TestClient(app) as c:
        yield c
    turn_jobs.JOBS.clear()


def test_submit_then_poll_delivers_a_turn_longer_than_one_poll(client, monkeypatch):
    async def slow_turn(_req: TurnRequest) -> TurnResponse:
        await asyncio.sleep(0.2)
        return TurnResponse(
            text="Supremme de Luxe…", output_tokens=1787, model="claude-opus-4-7", stop_reason="end_turn"
        )

    monkeypatch.setattr(turn_api.aire_route, "turn_via_aire", slow_turn)

    r = client.post("/v1/turn/jobs", json=REQ, headers=HEADERS)
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    assert job_id

    r = client.get(f"/v1/turn/jobs/{job_id}", params={"wait_s": 0.01}, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["status"] == "running"

    r = client.get(f"/v1/turn/jobs/{job_id}", params={"wait_s": 5}, headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "done"
    assert body["response"]["text"] == "Supremme de Luxe…"
    assert body["response"]["output_tokens"] == 1787

    # Recogido = borrado. El segundo cliente que pregunte recibe la señal de reinicio.
    assert client.get(f"/v1/turn/jobs/{job_id}", headers=HEADERS).status_code == 404


def test_the_same_job_id_posted_twice_runs_one_turn(client, monkeypatch):
    """El alta es idempotente por `job_id` del cliente: la repetición que el
    ingress entrega tarde (arranque en frío, 2026-09-23) no cuesta otro turno."""
    runs = {"n": 0}

    async def counted_turn(_req: TurnRequest) -> TurnResponse:
        runs["n"] += 1
        await asyncio.sleep(0.05)
        return TurnResponse(text="una sola vez", output_tokens=3, model="m", stop_reason="end_turn")

    monkeypatch.setattr(turn_api.aire_route, "turn_via_aire", counted_turn)
    req = {**REQ, "job_id": "a3f0c9d1e2b84f7a9c6d5e4f3a2b1c0d"}

    first = client.post("/v1/turn/jobs", json=req, headers=HEADERS)
    second = client.post("/v1/turn/jobs", json=req, headers=HEADERS)
    assert (first.status_code, second.status_code) == (202, 202)
    assert first.json()["job_id"] == second.json()["job_id"] == req["job_id"]

    body = client.get(f"/v1/turn/jobs/{req['job_id']}", params={"wait_s": 5}, headers=HEADERS).json()
    assert body["status"] == "done"
    assert body["response"]["text"] == "una sola vez"
    assert runs["n"] == 1


def test_a_job_id_that_is_not_a_token_is_rejected_not_run(client):
    r = client.post("/v1/turn/jobs", json={**REQ, "job_id": "../otro boleto"}, headers=HEADERS)
    assert r.status_code == 422


def test_unknown_job_is_404(client):
    assert client.get("/v1/turn/jobs/deadbeef", headers=HEADERS).status_code == 404


def test_no_token_is_refused_on_both_routes(client):
    assert client.post("/v1/turn/jobs", json=REQ).status_code == 401
    assert client.get("/v1/turn/jobs/x").status_code == 401


def test_a_turn_that_raises_surfaces_the_same_way_as_the_sync_path(client, monkeypatch):
    async def bad_turn(_req: TurnRequest) -> TurnResponse:
        await asyncio.sleep(0)
        raise RuntimeError("AIRE dijo que no")

    monkeypatch.setattr(turn_api.aire_route, "turn_via_aire", bad_turn)
    job_id = client.post("/v1/turn/jobs", json=REQ, headers=HEADERS).json()["job_id"]
    with pytest.raises(RuntimeError, match="AIRE dijo que no"):
        client.get(f"/v1/turn/jobs/{job_id}", params={"wait_s": 5}, headers=HEADERS)


# --- boleto durable (2026-09-23): el runner reiniciado contesta desde su fila ------


@pytest.fixture
def ledger(monkeypatch):
    """Un ledger en RAM colgado del registro real; un 'restart' es `JOBS.clear()`
    más un `claimed_by` nuevo sobre el mismo ledger."""
    from tests.shared.fake_ledger import FakeLedger

    fake = FakeLedger()
    monkeypatch.setattr(turn_jobs.JOBS, "ledger", fake)
    monkeypatch.setattr(turn_jobs, "LEDGER", fake)
    return fake


def _restart(monkeypatch, replica: str) -> None:
    turn_jobs.JOBS.clear()
    monkeypatch.setattr(turn_jobs.JOBS, "claimed_by", replica)


def _settle(seconds: float = 0.05) -> None:
    import time

    time.sleep(seconds)


JOB = {**REQ, "job_id": "b7e2c1d0a9f84c3e8d5a6b7c8d9e0f1a"}


def test_a_runner_restart_mid_turn_resumes_the_job_under_the_same_id(client, monkeypatch, ledger):
    seen: list[TurnRequest] = []

    async def turn(req: TurnRequest) -> TurnResponse:
        seen.append(req)
        if not req.resumed:
            await asyncio.sleep(60)  # el proceso A muere antes de terminar
        return TurnResponse(text="reanudado", output_tokens=5, model="m", stop_reason="end_turn")

    monkeypatch.setattr(turn_api.aire_route, "turn_via_aire", turn)
    assert client.post("/v1/turn/jobs", json=JOB, headers=HEADERS).status_code == 202
    assert ledger.rows[JOB["job_id"]]["status"] == "running"

    _restart(monkeypatch, "replica-b")
    ledger.age(JOB["job_id"])
    r = client.get(f"/v1/turn/jobs/{JOB['job_id']}", params={"wait_s": 5}, headers=HEADERS)
    assert r.status_code == 200 and r.json()["status"] == "done"
    assert r.json()["response"]["text"] == "reanudado"
    assert [req.resumed for req in seen] == [False, True]
    assert seen[1].user_text == REQ["user_text"] and seen[1].job_id == JOB["job_id"]
    assert ledger.rows[JOB["job_id"]]["attempts"] == 2


def test_a_turn_finished_before_the_restart_is_served_from_the_row_without_running_again(client, monkeypatch, ledger):
    runs = {"n": 0}

    async def turn(_req: TurnRequest) -> TurnResponse:
        runs["n"] += 1
        return TurnResponse(text="una vez", output_tokens=2, model="m", stop_reason="end_turn")

    monkeypatch.setattr(turn_api.aire_route, "turn_via_aire", turn)
    client.post("/v1/turn/jobs", json=JOB, headers=HEADERS)
    assert (
        client.get(f"/v1/turn/jobs/{JOB['job_id']}", params={"wait_s": 5}, headers=HEADERS).json()["status"] == "done"
    )
    _settle()

    _restart(monkeypatch, "replica-b")
    r = client.get(f"/v1/turn/jobs/{JOB['job_id']}", params={"wait_s": 1}, headers=HEADERS)
    assert r.status_code == 200 and r.json()["status"] == "done" and r.json()["response"]["text"] == "una vez"
    again = client.post("/v1/turn/jobs", json=JOB, headers=HEADERS)
    assert again.status_code == 202 and again.json()["job_id"] == JOB["job_id"]
    assert runs["n"] == 1


def test_a_second_restart_is_refused_as_attempts_exhausted(client, monkeypatch, ledger):
    async def never(_req: TurnRequest) -> TurnResponse:
        await asyncio.sleep(60)
        raise AssertionError("unreachable")

    monkeypatch.setattr(turn_api.aire_route, "turn_via_aire", never)
    client.post("/v1/turn/jobs", json=JOB, headers=HEADERS)
    _restart(monkeypatch, "replica-b")
    ledger.age(JOB["job_id"])
    assert (
        client.get(f"/v1/turn/jobs/{JOB['job_id']}", params={"wait_s": 0.01}, headers=HEADERS).json()["status"]
        == "running"
    )
    _restart(monkeypatch, "replica-c")
    ledger.age(JOB["job_id"])
    r = client.get(f"/v1/turn/jobs/{JOB['job_id']}", params={"wait_s": 0.01}, headers=HEADERS)
    assert r.status_code == 502 and "attempts_exhausted" in r.json()["detail"]


def test_a_job_another_replica_still_beats_is_not_re_run(client, monkeypatch, ledger):
    runs = {"n": 0}

    async def turn(_req: TurnRequest) -> TurnResponse:
        runs["n"] += 1
        await asyncio.sleep(60)
        raise AssertionError("unreachable")

    monkeypatch.setattr(turn_api.aire_route, "turn_via_aire", turn)
    client.post("/v1/turn/jobs", json=JOB, headers=HEADERS)
    _restart(monkeypatch, "replica-b")  # la fila sigue fresca: A sigue latiendo
    r = client.get(f"/v1/turn/jobs/{JOB['job_id']}", params={"wait_s": 0.01}, headers=HEADERS)
    assert r.status_code == 200 and r.json()["status"] == "running"
    assert runs["n"] == 1


def test_the_live_run_receives_the_attachments_the_row_does_not_keep(client, monkeypatch, ledger):
    """P0 2026-09-25: la fila no guarda los adjuntos (MB de base64) y eso está
    bien; lo que NO está bien es que la corrida en vivo se reconstruyera desde la
    fila. Desde c74dbf4 (v4.40.2) cada imagen se tiraba en el alta: el gateway
    logueaba `attachments_forwarded count=1` y el runner `has_attachments=false`,
    e Insult contestaba a ciegas. La prueba de al lado sólo miraba la fila."""
    seen: dict[str, object] = {}

    async def turn(req: TurnRequest) -> TurnResponse:
        seen["attachments"] = req.attachments
        seen["resumed"] = req.resumed
        return TurnResponse(text="la vi", output_tokens=3, model="m", stop_reason="end_turn")

    monkeypatch.setattr(turn_api.aire_route, "turn_via_aire", turn)
    image = {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "aGk="}}
    client.post("/v1/turn/jobs", json={**JOB, "attachments": [image]}, headers=HEADERS)
    body = client.get(f"/v1/turn/jobs/{JOB['job_id']}", params={"wait_s": 5}, headers=HEADERS).json()

    assert body["status"] == "done"
    assert seen["attachments"] == [image]
    assert seen["resumed"] is False
    # Resistencia: la fila sigue sin la imagen, sólo con la marca de que la hubo.
    assert "attachments" not in ledger.rows[JOB["job_id"]]["payload"]
    assert ledger.rows[JOB["job_id"]]["payload"]["has_attachments"] is True


def test_a_job_with_attachments_is_not_resumable(client, monkeypatch, ledger):
    async def never(_req: TurnRequest) -> TurnResponse:
        await asyncio.sleep(60)
        raise AssertionError("unreachable")

    monkeypatch.setattr(turn_api.aire_route, "turn_via_aire", never)
    with_image = {**JOB, "attachments": [{"type": "image", "source": {"data": "aGk="}}]}
    client.post("/v1/turn/jobs", json=with_image, headers=HEADERS)
    assert "attachments" not in ledger.rows[JOB["job_id"]]["payload"]
    assert ledger.rows[JOB["job_id"]]["payload"]["has_attachments"] is True
    _restart(monkeypatch, "replica-b")
    ledger.age(JOB["job_id"])
    r = client.get(f"/v1/turn/jobs/{JOB['job_id']}", params={"wait_s": 0.5}, headers=HEADERS)
    assert r.status_code == 502 and "not_resumable" in r.json()["detail"]
    _settle()
    assert ledger.rows[JOB["job_id"]]["status"] == "failed"
    again = client.get(f"/v1/turn/jobs/{JOB['job_id']}", params={"wait_s": 0.01}, headers=HEADERS)
    assert again.status_code == 502  # la fila lo recuerda tras el drop en RAM


def test_with_the_ledger_down_the_contract_is_exactly_ram_only(client, monkeypatch, ledger):
    ledger.fail = True

    async def turn(_req: TurnRequest) -> TurnResponse:
        return TurnResponse(text="ram", output_tokens=1, model="m", stop_reason="end_turn")

    monkeypatch.setattr(turn_api.aire_route, "turn_via_aire", turn)
    job_id = client.post("/v1/turn/jobs", json=REQ, headers=HEADERS).json()["job_id"]
    assert client.get(f"/v1/turn/jobs/{job_id}", params={"wait_s": 5}, headers=HEADERS).json()["status"] == "done"
    assert client.get(f"/v1/turn/jobs/{job_id}", headers=HEADERS).status_code == 404
    assert ledger.rows == {}
