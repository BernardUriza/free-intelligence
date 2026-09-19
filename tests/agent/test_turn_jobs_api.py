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
