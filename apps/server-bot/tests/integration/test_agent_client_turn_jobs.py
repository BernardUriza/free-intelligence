"""AgentRunnerClient pide el turno con boleto y lo espera por polls (sin red).

Root cause, 2026-09-19: el ingress de Container Apps corta toda request a los
240 s. Un turno de Vultur tardó 326.9 s, AIRE lo entregó completo, y el cliente
—colgado de UNA request— ya lo había dado por perdido. Positiva: alta 202 →
polls `running` → poll `done` entrega el turno, y ninguna request individual
lleva el presupuesto del turno. Resistencia: un runner viejo (404 al alta) cae
al camino síncrono UNA vez; un boleto que desaparece a media espera (el runner
se reinició) es `RunnerDownError`, nunca un turno rechazado; y un poll que se
cae por red se vuelve a preguntar en vez de tirar la respuesta.
"""

from __future__ import annotations

from typing import ClassVar

import httpx
import pytest

from persona_core.runner import agent_client as mod
from persona_core.runner.agent_client import AgentRunnerClient, RunnerDownError


class _Resp:
    def __init__(self, status_code: int, body: dict | None = None) -> None:
        self.status_code = status_code
        self._body = body or {}
        self.text = str(body)

    def json(self) -> dict:
        return self._body


TURN = {"text": "Supremme de Luxe…", "output_tokens": 1787, "model": "claude-opus-4-7", "stop_reason": "end_turn"}


class _ScriptedClient:
    """Cada request (POST o GET) consume el siguiente elemento del guion."""

    script: ClassVar[list] = []
    calls: ClassVar[list[tuple[str, str]]] = []
    bodies: ClassVar[list[dict]] = []

    def __init__(self, *a, **k) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def _next(self, method: str, url: str):
        _ScriptedClient.calls.append((method, url))
        item = _ScriptedClient.script[min(len(_ScriptedClient.calls) - 1, len(_ScriptedClient.script) - 1)]
        if isinstance(item, BaseException):
            raise item
        return item

    async def post(self, url, json=None, headers=None):
        _ScriptedClient.bodies.append(json or {})
        return await self._next("POST", url)

    async def get(self, url, headers=None):
        return await self._next("GET", url)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("persona_core.runner.agent_client.httpx.AsyncClient", _ScriptedClient)

    async def _no_sleep(_s):
        return None

    monkeypatch.setattr("persona_core.runner.agent_client.asyncio.sleep", _no_sleep)
    _ScriptedClient.script = []
    _ScriptedClient.calls = []
    _ScriptedClient.bodies = []
    return AgentRunnerClient("http://runner", "tok", timeout_s=600.0)


def _msgs() -> list[dict]:
    return [{"role": "user", "content": "investiga a Supremme de Luxe"}]


@pytest.mark.asyncio
async def test_submit_then_polls_until_done_delivers_the_turn(client):
    _ScriptedClient.script = [
        _Resp(202, {"job_id": "j1", "status": "running"}),
        _Resp(200, {"job_id": "j1", "status": "running"}),
        _Resp(200, {"job_id": "j1", "status": "running"}),
        _Resp(200, {"job_id": "j1", "status": "done", "response": TURN}),
    ]
    out = await client.chat("sys", _msgs())
    assert out.text == "Supremme de Luxe…"
    methods = [m for m, _ in _ScriptedClient.calls]
    assert methods == ["POST", "GET", "GET", "GET"]
    assert _ScriptedClient.calls[0][1].endswith("/v1/turn/jobs")
    assert "/v1/turn/jobs/j1?wait_s=" in _ScriptedClient.calls[1][1]


@pytest.mark.asyncio
async def test_no_single_request_carries_the_turn_budget(client, monkeypatch):
    """El read timeout de cada request vive bajo el tope del ingress aunque el
    presupuesto del turno sea de 10 minutos."""
    seen: list[httpx.Timeout] = []

    class _Spy(_ScriptedClient):
        def __init__(self, *a, timeout=None, **k) -> None:
            seen.append(timeout)

    monkeypatch.setattr("persona_core.runner.agent_client.httpx.AsyncClient", _Spy)
    _ScriptedClient.script = [
        _Resp(202, {"job_id": "j1"}),
        _Resp(200, {"job_id": "j1", "status": "done", "response": TURN}),
    ]
    await client.chat("sys", _msgs(), timeout_s=600.0)
    assert seen and all(t.read is not None and t.read < 240.0 for t in seen)


@pytest.mark.asyncio
async def test_an_old_runner_without_jobs_falls_back_to_the_sync_turn_once(client):
    _ScriptedClient.script = [_Resp(404, {"detail": "Not Found"}), _Resp(200, TURN)]
    out = await client.chat("sys", _msgs())
    assert out.text == "Supremme de Luxe…"
    assert [(m, u.rsplit("/", 1)[-1]) for m, u in _ScriptedClient.calls] == [("POST", "jobs"), ("POST", "turn")]


@pytest.mark.asyncio
async def test_a_job_that_vanishes_mid_poll_is_runner_down_not_a_rejected_turn(client):
    _ScriptedClient.script = [
        _Resp(202, {"job_id": "j1"}),
        _Resp(200, {"job_id": "j1", "status": "running"}),
        _Resp(404, {"detail": "unknown turn job 'j1'"}),
    ]
    with pytest.raises(RunnerDownError, match="vanished"):
        await client.chat("sys", _msgs())


@pytest.mark.asyncio
async def test_a_poll_that_drops_on_the_network_is_asked_again(client):
    _ScriptedClient.script = [
        _Resp(202, {"job_id": "j1"}),
        httpx.ReadTimeout("poll dropped"),
        httpx.ConnectError("blip"),
        _Resp(200, {"job_id": "j1", "status": "done", "response": TURN}),
    ]
    out = await client.chat("sys", _msgs())
    assert out.text == "Supremme de Luxe…"
    assert len(_ScriptedClient.calls) == 4


@pytest.mark.asyncio
async def test_a_submit_lost_in_a_cold_start_is_posted_again_with_the_same_job_id(client):
    """2026-09-23: el runner (min=0) tardó 169 s en aceptar el alta; el cliente la
    dio por perdida a los 60 s y el host se rindió. El alta se repite con el
    mismo boleto — el runner deduplica — y el turno llega."""
    _ScriptedClient.script = [
        httpx.ReadTimeout("el ingress retiene el alta mientras el runner arranca"),
        _Resp(202, {"job_id": "j-cliente", "status": "running"}),
        _Resp(200, {"job_id": "j-cliente", "status": "done", "response": TURN}),
    ]
    fired = []
    out = await client.chat("sys", _msgs(), timeout_s=600.0, on_timeout=lambda: fired.append(1))
    assert out.text == "Supremme de Luxe…"
    assert [m for m, _ in _ScriptedClient.calls] == ["POST", "POST", "GET"]
    ids = {b.get("job_id") for b in _ScriptedClient.bodies}
    assert len(ids) == 1 and ids != {None}  # las dos altas llevan el MISMO boleto
    assert fired == [1]


@pytest.mark.asyncio
async def test_the_submit_read_timeout_covers_a_cold_start_but_not_the_ingress_cap(client, monkeypatch):
    seen: list[httpx.Timeout] = []

    class _Spy(_ScriptedClient):
        def __init__(self, *a, timeout=None, **k) -> None:
            seen.append(timeout)

    monkeypatch.setattr("persona_core.runner.agent_client.httpx.AsyncClient", _Spy)
    _ScriptedClient.script = [
        _Resp(202, {"job_id": "j1"}),
        _Resp(200, {"job_id": "j1", "status": "done", "response": TURN}),
    ]
    await client.chat("sys", _msgs(), timeout_s=600.0)
    submit_read = seen[0].read
    assert submit_read is not None and 169.0 < submit_read < 240.0


@pytest.mark.asyncio
async def test_a_submit_that_never_lands_within_the_turn_budget_is_runner_down(client, monkeypatch):
    ticks = {"n": 0}

    def _clock() -> float:  # start, submit_deadline, connect_deadline; después el reloj ya se pasó
        ticks["n"] += 1
        return 0.0 if ticks["n"] <= 3 else 1000.0

    monkeypatch.setattr(mod.time, "monotonic", _clock)
    _ScriptedClient.script = [httpx.ReadTimeout("nunca contestó")]
    with pytest.raises(RunnerDownError, match="read timeout"):
        await client.chat("sys", _msgs(), timeout_s=600.0)
    assert [m for m, _ in _ScriptedClient.calls] == ["POST"]


@pytest.mark.asyncio
async def test_the_turn_budget_exhausted_fires_on_timeout_once_and_is_runner_down(client, monkeypatch):
    ticks = {"n": 0}

    def _clock() -> float:  # las primeras lecturas son el arranque; después el reloj ya se pasó
        ticks["n"] += 1
        return 0.0 if ticks["n"] <= 4 else 1000.0

    monkeypatch.setattr(mod.time, "monotonic", _clock)
    _ScriptedClient.script = [_Resp(202, {"job_id": "j1"}), _Resp(200, {"job_id": "j1", "status": "running"})]
    fired = []
    with pytest.raises(RunnerDownError, match="unfinished"):
        await client.chat("sys", _msgs(), timeout_s=600.0, on_timeout=lambda: fired.append(1))
    assert fired == [1]


@pytest.mark.asyncio
async def test_a_given_job_id_travels_in_every_submit_and_names_the_poll(client):
    """El gateway manda su turn_id como job_id: una reanudación del gateway
    re-postea el MISMO job y el runner deduplica en vez de re-correr."""
    _ScriptedClient.script = [
        httpx.ReadTimeout("frío"),
        _Resp(202, {"job_id": "j-given", "status": "running"}),
        _Resp(200, {"job_id": "j-given", "status": "done", "response": TURN}),
    ]
    out = await client.chat("sys", _msgs(), job_id="j-given")
    assert out.text == "Supremme de Luxe…"
    assert {b.get("job_id") for b in _ScriptedClient.bodies} == {"j-given"}
    assert "/v1/turn/jobs/j-given?wait_s=" in _ScriptedClient.calls[-1][1]
