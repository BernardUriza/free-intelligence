"""`GET /v1/turn/jobs/{id}/events` — los `tool_call` de un turno, en vivo.

Positiva: un turno que invoca dos herramientas las entrega por SSE con `id`
secuencial mientras corre, y cierra con `event: done`; un cliente que se
reconecta con `Last-Event-ID` recibe sólo lo que le falta. Resistencia: id
desconocido 404, sin token 401, y un turno sin bitácora (terminó antes) cierra
de inmediato en vez de colgar.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from persona_runner.api import turn as turn_api
from persona_runner.core.schemas import TurnRequest, TurnResponse
from persona_runner.engine import aire_route, turn_events, turn_jobs

TOKEN = "tok-1"  # noqa: S105 — fixture, no un secreto
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
REQ = {
    "channel_id": "d2742db6-a382-4aef-89f6-a29a2e0795b4",
    "user_id": "907264175246569543",
    "user_text": "¿qué opinas de las inmobiliarias rapaces?",
    "persona_id": "insult",
    "job_id": "job-yodo-1",
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("persona_runner.core.config.RUNNER_AUTH_TOKEN", TOKEN)
    turn_jobs.JOBS.clear()
    turn_events.clear()
    app = FastAPI()
    app.include_router(turn_api.router)
    with TestClient(app) as c:
        yield c
    turn_jobs.JOBS.clear()
    turn_events.clear()


def _tool(name: str, tool_id: str) -> dict:
    return {"type": "tool_call", "tool": {"name": name, "id": tool_id, "server": None, "is_error": None}}


async def _tool_heavy_turn(req: TurnRequest) -> TurnResponse:
    turn_events.open_log(req.job_id)
    try:
        turn_events.emit(req.job_id, _tool("mcp__memory__recall", "t1"))
        await asyncio.sleep(0.05)
        turn_events.emit(req.job_id, _tool("WebSearch", "t2"))
        await asyncio.sleep(0.15)
        return TurnResponse(text="listo", model="claude-opus-4-7", stop_reason="end_turn")
    finally:
        turn_events.close_log(req.job_id)


def _read_sse(client: TestClient, job_id: str, **kw) -> list[tuple[str | None, str | None, dict]]:
    """[(id, event, data)] hasta que el stream cierra."""
    out, cur_id, cur_event = [], None, None
    with client.stream(
        "GET", f"/v1/turn/jobs/{job_id}/events", headers={**HEADERS, **kw.pop("headers", {})}, **kw
    ) as r:
        assert r.status_code == 200, r.status_code
        assert r.headers["content-type"].startswith("text/event-stream")
        for line in r.iter_lines():
            if line.startswith("id: "):
                cur_id = line[4:]
            elif line.startswith("event: "):
                cur_event = line[7:]
            elif line.startswith("data: "):
                out.append((cur_id, cur_event, json.loads(line[6:])))
                cur_id, cur_event = None, None
    return out


def test_the_tools_of_a_running_turn_stream_live_and_the_log_closes_with_done(client, monkeypatch):
    monkeypatch.setattr(aire_route, "turn_via_aire", _tool_heavy_turn)
    assert client.post("/v1/turn/jobs", json=REQ, headers=HEADERS).status_code == 202

    events = _read_sse(client, "job-yodo-1")

    assert [e[0] for e in events] == ["1", "2", None]
    assert [e[2].get("type") for e in events[:2]] == ["tool_call", "tool_call"]
    assert [e[2]["tool"]["name"] for e in events[:2]] == ["mcp__memory__recall", "WebSearch"]
    assert events[-1][1] == "done"
    # El resultado sigue viajando por el boleto, no por la bitácora.
    r = client.get("/v1/turn/jobs/job-yodo-1", params={"wait_s": 5}, headers=HEADERS)
    assert r.json()["status"] == "done" and r.json()["response"]["text"] == "listo"


def test_a_reconnect_with_last_event_id_replays_only_what_is_missing(client, monkeypatch):
    monkeypatch.setattr(aire_route, "turn_via_aire", _tool_heavy_turn)
    client.post("/v1/turn/jobs", json=REQ, headers=HEADERS)

    events = _read_sse(client, "job-yodo-1", headers={"Last-Event-ID": "1"})

    assert [e[0] for e in events] == ["2", None]
    assert events[0][2]["tool"]["name"] == "WebSearch"


def test_after_query_is_the_cursor_for_clients_without_the_header(client, monkeypatch):
    monkeypatch.setattr(aire_route, "turn_via_aire", _tool_heavy_turn)
    client.post("/v1/turn/jobs", json=REQ, headers=HEADERS)
    events = _read_sse(client, "job-yodo-1", params={"after": 2})
    assert [e[1] for e in events] == ["done"]


def test_a_known_job_without_a_log_closes_at_once_instead_of_hanging(client, monkeypatch):
    async def silent_turn(_req: TurnRequest) -> TurnResponse:
        return TurnResponse(text="sin herramientas")

    monkeypatch.setattr(aire_route, "turn_via_aire", silent_turn)
    client.post("/v1/turn/jobs", json=REQ, headers=HEADERS)
    events = _read_sse(client, "job-yodo-1")
    assert [e[1] for e in events] == ["done"]


def test_unknown_job_is_404_and_no_token_is_401(client):
    assert client.get("/v1/turn/jobs/nope/events", headers=HEADERS).status_code == 404
    assert client.get("/v1/turn/jobs/job-yodo-1/events").status_code == 401


def test_turn_via_aire_opens_the_log_before_the_turn_and_closes_it_after(monkeypatch):
    seen: dict[str, object] = {}

    async def fake_run_turn(req, base_id, casita, state):
        log = turn_events.get_log(req.job_id)
        seen["open_during"] = log is not None and not log.closed
        turn_events.emit(req.job_id, _tool("WebSearch", "t9"))
        return TurnResponse(text="ok")

    monkeypatch.setattr(aire_route, "_run_turn", fake_run_turn)
    req = TurnRequest.model_validate(REQ)
    asyncio.run(aire_route.turn_via_aire(req))
    log = turn_events.get_log("job-yodo-1")
    assert seen["open_during"] is True
    assert log is not None and log.closed and len(log) == 1
