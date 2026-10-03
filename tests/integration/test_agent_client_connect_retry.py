"""Connect-level retry for AgentRunnerClient (no network).

Root cause, 2026-06-21: Alex sent an image; the runner was alive + idle but a
single transient ``ConnectTimeout`` (10s, the TCP connect never completed) was
turned STRAIGHT into ``RunnerDownError`` with zero retries, so a one-off blip
summoned ALICE — who never receives the image and answers blind. A ConnectTimeout
/ ConnectError happens BEFORE the request body is sent, so the turn provably never
reached the runner: re-POSTing is safe (no duplicate turn) and is the correct
resilience move.

Resistance case (the one that makes this safe): a ``ReadTimeout`` means the
request MAY have landed and be processing. Since 2026-09-23 the alta carries a
client-chosen ``job_id`` the runner deduplicates on, so the re-POST is safe — but
ONLY with the same id. A fresh id on retry would be the double-spend again.
"""

from __future__ import annotations

from typing import ClassVar

import httpx
import pytest

from persona_core.runner.agent_client import (
    AgentRunnerClient,
    PersonaTurnError,
    RunnerDownError,
)


def _messages() -> list[dict]:
    return [{"role": "user", "content": "mira esta imagen"}]


class _Resp:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code
        self.text = "ok"

    def json(self) -> dict:
        return {"text": "ok", "stop_reason": "end_turn", "model": "agent-runner"}


class _ScriptedClient:
    """Raises a scripted sequence of transport errors, then returns a resp.

    ``script`` is a list where each element is either an exception instance (raise
    it on that POST attempt) or an ``_Resp`` (return it). ``calls`` counts POSTs.
    """

    script: ClassVar[list] = []
    calls: ClassVar[int] = 0
    job_ids: ClassVar[list] = []

    def __init__(self, *a, **k) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        idx = _ScriptedClient.calls
        _ScriptedClient.calls += 1
        _ScriptedClient.job_ids.append((json or {}).get("job_id"))
        item = _ScriptedClient.script[min(idx, len(_ScriptedClient.script) - 1)]
        if isinstance(item, BaseException):
            raise item
        return item


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("persona_core.runner.agent_client.httpx.AsyncClient", _ScriptedClient)

    # No real backoff sleeps in tests.
    async def _no_sleep(_s):
        return None

    monkeypatch.setattr("persona_core.runner.agent_client.asyncio.sleep", _no_sleep)
    _ScriptedClient.script = []
    _ScriptedClient.calls = 0
    _ScriptedClient.job_ids = []
    return AgentRunnerClient("http://runner", "tok")


@pytest.mark.asyncio
async def test_connect_timeout_retries_then_succeeds(client):
    """Two transient ConnectTimeouts then a good response → NO failover, the turn
    is served by the runner. This is the Alex-image incident, fixed."""
    _ScriptedClient.script = [
        httpx.ConnectTimeout("syn dropped"),
        httpx.ConnectTimeout("syn dropped"),
        _Resp(200),
    ]
    out = await client.chat("sys", _messages())
    assert out.text == "ok"
    assert _ScriptedClient.calls == 3  # retried twice, succeeded on the third


@pytest.mark.asyncio
async def test_connect_error_retries_then_succeeds(client):
    """ConnectError (refused) is also pre-send → retryable."""
    _ScriptedClient.script = [httpx.ConnectError("refused"), _Resp(200)]
    out = await client.chat("sys", _messages())
    assert out.text == "ok"
    assert _ScriptedClient.calls == 2


@pytest.mark.asyncio
async def test_connect_timeout_exhausts_then_runner_down(client):
    """A genuinely unreachable runner still fails over after the budget is spent.

    Here every connect fails INSTANTLY, so the clock barely moves and the hard
    attempt cap is what ends it — that is the branch this asserts.
    """
    _ScriptedClient.script = [httpx.ConnectTimeout("down")]  # always raises
    with pytest.raises(RunnerDownError) as err:
        await client.chat("sys", _messages())
    assert _ScriptedClient.calls == 9  # 1 + 8 retries
    assert "attempts exhausted" in str(err.value)


@pytest.mark.asyncio
async def test_connect_budget_covers_a_rolling_update(client):
    """El caso que motivó el presupuesto: el runner rota y el socket se rechaza
    durante decenas de segundos.

    La política vieja (2 reintentos, base 0.25s) gastaba 0.75s y declaraba el
    cerebro muerto mientras el deploy seguía en vuelo, así que un turno normal
    moría por un despliegue. Ocho reintentos con backoff topado cubren ~32s de
    ventana, que es la escala real de un rolling update de Container Apps más el
    arranque en frío del runner (min=0).
    """
    _ScriptedClient.script = [httpx.ConnectError("refused")] * 6 + [_Resp(200)]
    out = await client.chat("sys", _messages())
    assert out.text == "ok"
    assert _ScriptedClient.calls == 7  # sobrevivió al swap, turno TARDÍO no perdido


@pytest.mark.asyncio
async def test_el_presupuesto_de_reloj_corta_antes_que_los_intentos(monkeypatch):
    """RESISTENCIA: un connect que CUELGA no puede vivir más que el presupuesto.

    Sin corte por reloj, ocho reintentos de un connect que tarda su timeout
    completo (10s) tendrían al usuario esperando minutos por un cerebro que ya
    está muerto. El tope de intentos no protege de eso — sólo el reloj. Aquí cada
    intento consume 20s de reloj simulado, así que el presupuesto de 45s se acaba
    en el tercero y el error lo dice.
    """
    monkeypatch.setattr("persona_core.runner.agent_client.httpx.AsyncClient", _ScriptedClient)

    async def _no_sleep(_s):
        return None

    monkeypatch.setattr("persona_core.runner.agent_client.asyncio.sleep", _no_sleep)

    reloj = {"t": 0.0}

    def _monotonic():
        reloj["t"] += 20.0  # cada lectura avanza el reloj: un connect que cuelga
        return reloj["t"]

    monkeypatch.setattr("persona_core.runner.agent_client.time.monotonic", _monotonic)
    _ScriptedClient.script = [httpx.ConnectTimeout("hangs")]
    _ScriptedClient.calls = 0

    cliente = AgentRunnerClient("http://runner", "tok")
    with pytest.raises(RunnerDownError) as err:
        await cliente.chat("sys", _messages())

    assert _ScriptedClient.calls < 9, "el reloj tenía que cortar antes que el tope de intentos"
    assert "budget exhausted" in str(err.value)


@pytest.mark.asyncio
async def test_read_timeout_is_retried_only_under_the_same_job_id(client):
    """RESISTANCE: a ReadTimeout means the request may have landed. The re-POST
    is safe ONLY because it repeats the same job_id the runner deduplicates on —
    a fresh id per attempt would be the double-spend this test used to forbid."""
    _ScriptedClient.script = [httpx.ReadTimeout("processing"), _Resp(200)]
    out = await client.chat("sys", _messages())
    assert out.text == "ok"
    assert _ScriptedClient.calls == 2
    assert _ScriptedClient.job_ids[0] and len(set(_ScriptedClient.job_ids)) == 1


@pytest.mark.asyncio
async def test_502_retries_then_succeeds(client):
    """The Vultur 2026-07-24 incident: the runner returns 502 ('agent loop
    failed') because a rolling update's SIGTERM killed the SDK mid-generation.
    The new revision comes up → the re-POST succeeds → a LATE turn, not a '…'."""
    _ScriptedClient.script = [_Resp(502), _Resp(502), _Resp(200)]
    out = await client.chat("sys", _messages())
    assert out.text == "ok"
    assert _ScriptedClient.calls == 3  # retried twice, served on the third


@pytest.mark.asyncio
async def test_503_retries_then_succeeds(client):
    """503 (runner not-ready during the revision swap) is the same transient
    class as 502 — retry, don't fail over."""
    _ScriptedClient.script = [_Resp(503), _Resp(200)]
    out = await client.chat("sys", _messages())
    assert out.text == "ok"
    assert _ScriptedClient.calls == 2


@pytest.mark.asyncio
async def test_502_exhausts_then_runner_down(client):
    """A PERSISTENT 502 (a real agent-loop bug, not a restart) exhausts the
    bounded retries and degrades honestly — never double-spends forever."""
    _ScriptedClient.script = [_Resp(502)]  # always 502
    with pytest.raises(RunnerDownError):
        await client.chat("sys", _messages())
    assert _ScriptedClient.calls == 3  # 1 + 2 transient retries


@pytest.mark.asyncio
async def test_500_is_not_retried(client):
    """RESISTANCE: a 500 is a DEFINED internal error (a bug to see), not the
    restart-class 502/503. It stays a single-shot RunnerDownError."""
    _ScriptedClient.script = [_Resp(500)]
    with pytest.raises(RunnerDownError):
        await client.chat("sys", _messages())
    assert _ScriptedClient.calls == 1  # NOT retried


@pytest.mark.asyncio
async def test_4xx_is_not_retried(client):
    """RESISTANCE: a 4xx is a rejected turn (the runner is UP). Never retried,
    and it degrades as PersonaTurnError so no fake-ALICE failover fires."""
    _ScriptedClient.script = [_Resp(422)]
    with pytest.raises(PersonaTurnError):
        await client.chat("sys", _messages())
    assert _ScriptedClient.calls == 1  # NOT retried
