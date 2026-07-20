"""Gateway boot resilience — the ActivationFailed / crashloop root fix.

Signature being killed (memory `reference_activationfailed_gateway_hang`): a new
revision boots, logs `agent_runner_client_configured`, then dies silently; the
ACA StartUp probe reports `Probe of StartUp failed with status code: 1` in bursts
and the replica restarts every ~5 min, burning another Discord IDENTIFY each
time. Three defects fed it, one test class each:

1. `await memory.connect()` ran BEFORE port 8788 bound — a cold Postgres starved
   the probe.
2. `asyncio.gather(*starts)` propagated ONE persona's login failure and tore the
   whole process down, `/invite` and healthy siblings included.
3. `/health` answered `{"status": "ok"}` with zero personas logged in — a proxy
   that lies (the 2026-06-13 boot-zombie shape).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from persona_gateway import app as app_mod
from persona_gateway.app import _connect_memory, _supervise_persona, _wait_until_bound
from persona_gateway.boot import GatewayBootState
from persona_gateway.invite_server import build_invite_app

TOKEN = "s3cr3t-token"  # noqa: S105 — fixture token, not a real secret


def _ready_client() -> SimpleNamespace:
    return SimpleNamespace(user=SimpleNamespace(id=1503983124982534284), respond_to_invite=AsyncMock())


def _booting_client() -> SimpleNamespace:
    """Logged in to nothing yet: on_ready has not fired, so .user is None."""
    return SimpleNamespace(user=None, respond_to_invite=AsyncMock())


# --- 3. /health tells the truth about serving -------------------------------


def test_health_reports_not_serving_while_personas_still_booting():
    app = build_invite_app({"alice": _booting_client(), "vultur": _booting_client()}, TOKEN)
    with TestClient(app) as http:
        body = http.get("/health").json()
    assert body["status"] == "ok"  # liveness: the process answers
    assert body["serving"] is False  # honesty: nobody can reply yet
    assert body["personas_ready"] == []
    assert body["personas_expected"] == ["alice", "vultur"]


def test_health_reports_serving_once_a_persona_is_ready():
    app = build_invite_app({"alice": _ready_client(), "vultur": _booting_client()}, TOKEN)
    with TestClient(app) as http:
        body = http.get("/health").json()
    assert body["serving"] is True
    assert body["personas_ready"] == ["alice"]


def test_health_excludes_a_persona_that_died_after_on_ready():
    """Resistance case: `.user` survives the session's death — `personas_down` wins."""
    boot = GatewayBootState()
    boot.mark_persona_down("vultur")
    app = build_invite_app({"alice": _ready_client(), "vultur": _ready_client()}, TOKEN, boot)
    with TestClient(app) as http:
        body = http.get("/health").json()
    assert body["personas_ready"] == ["alice"]
    assert body["personas_down"] == ["vultur"]
    assert body["serving"] is True  # alice still serves


def test_health_reports_db_connection_state():
    boot = GatewayBootState()
    app = build_invite_app({"alice": _ready_client()}, TOKEN, boot)
    with TestClient(app) as http:
        assert http.get("/health").json()["db_connected"] is False
        boot.mark_db_connected()
        assert http.get("/health").json()["db_connected"] is True


# --- 2. one persona's death never tears down the process ---------------------


@pytest.mark.asyncio
async def test_supervise_isolates_a_login_failure():
    boot = GatewayBootState()

    async def throttled_identify():
        raise ConnectionResetError("IDENTIFY rate limited")

    await _supervise_persona("vultur", throttled_identify(), boot)  # must NOT raise

    assert boot.is_down("vultur")


@pytest.mark.asyncio
async def test_supervise_marks_down_on_clean_session_exit():
    """`Client.start` returning at all means the session ended — that is a loss."""
    boot = GatewayBootState()

    async def session_ends():
        return None

    await _supervise_persona("alice", session_ends(), boot)

    assert boot.is_down("alice")


@pytest.mark.asyncio
async def test_supervise_lets_cancellation_through():
    """Resistance case: shutdown must cancel cleanly, not be swallowed as a death."""
    boot = GatewayBootState()

    async def never_ends():
        await asyncio.Event().wait()

    task = asyncio.create_task(_supervise_persona("alice", never_ends(), boot))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not boot.is_down("alice")


@pytest.mark.asyncio
async def test_one_persona_dying_leaves_its_sibling_running():
    boot = GatewayBootState()
    sibling_alive = asyncio.Event()

    async def dies():
        raise RuntimeError("token revoked")

    async def survives():
        sibling_alive.set()
        await asyncio.Event().wait()

    dead = asyncio.create_task(_supervise_persona("vultur", dies(), boot))
    alive = asyncio.create_task(_supervise_persona("alice", survives(), boot))
    await dead
    await asyncio.wait_for(sibling_alive.wait(), timeout=1)

    assert boot.is_down("vultur")
    assert not boot.is_down("alice")
    assert not alive.done()
    alive.cancel()
    with pytest.raises(asyncio.CancelledError):
        await alive


# --- 1. a cold Postgres degrades, never starves the probe --------------------


@pytest.mark.asyncio
async def test_db_failure_at_boot_degrades_instead_of_killing_the_process():
    boot = GatewayBootState()
    memory = SimpleNamespace(connect=AsyncMock(side_effect=OSError("connection refused")))

    await _connect_memory(memory, boot)  # must NOT raise

    assert boot.db_connected is False


@pytest.mark.asyncio
async def test_db_success_marks_connected():
    boot = GatewayBootState()
    memory = SimpleNamespace(connect=AsyncMock())

    await _connect_memory(memory, boot)

    assert boot.db_connected is True


@pytest.mark.asyncio
async def test_http_server_binds_before_postgres_and_before_discord_login(monkeypatch):
    """The ordering that kills the crashloop: bind → connect → login.

    Whatever blocks (a cold Postgres, a throttled IDENTIFY) must block AFTER port
    8788 is listening, so the ACA StartUp probe answers and the replica survives.
    """
    order: list[str] = []

    async def fake_connect():
        order.append("db_connect")

    memory = SimpleNamespace(connect=fake_connect, close=AsyncMock())
    # (memory, agent_client, tts_client, auto_tts_min_chars, invite_token, judge_client)
    shared = (memory, object(), None, 0, TOKEN, object())
    monkeypatch.setattr(app_mod, "_build_shared", lambda: shared)

    persona = SimpleNamespace(persona_id="alice", token_env="ALICE_DISCORD_TOKEN")
    monkeypatch.setattr(app_mod, "gateway_personas", lambda: [persona])
    monkeypatch.setenv("ALICE_DISCORD_TOKEN", "token")

    async def fake_start(_token):
        order.append("discord_login")
        raise RuntimeError("login refused")

    monkeypatch.setattr(
        app_mod,
        "PersonaClient",
        lambda *a, **kw: SimpleNamespace(user=None, start=fake_start),
    )

    server = SimpleNamespace(started=False)

    async def fake_serve():
        order.append("http_bind")
        server.started = True
        await asyncio.Event().wait()

    monkeypatch.setattr(app_mod, "_serve_invite_api", lambda *a: (server, fake_serve()))

    await asyncio.wait_for(app_mod._main(), timeout=5)

    assert order == ["http_bind", "db_connect", "discord_login"]
    memory.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_wait_until_bound_gives_up_instead_of_hanging_forever():
    """Resistance case: a server that never binds must not wedge the boot."""
    never = SimpleNamespace(started=False)

    bound = await _wait_until_bound(never, timeout=0.1)

    assert bound is False
