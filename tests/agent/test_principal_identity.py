"""F2 — identidad por superficie → principal canónico, en la puerta del runner.

Positiva: un `sub` de Auth0 ligado en `principal_identities` entra a
`turn_via_aire` (y al job persistido) como el snowflake bajo el que vive la
memoria. Resistencia: sin fila el id pasa tal cual (Discord sigue igual), un id
externo repetido en dos superficies NO se resuelve (colisión, no identidad),
y un Postgres caído degrada a "sin puente" en vez de matar el turno.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from persona_runner.api import turn as turn_api
from persona_runner.core.schemas import TurnRequest, TurnResponse
from persona_runner.engine import aire_route, principal_identity, turn_jobs

TOKEN = "tok-1"  # noqa: S105 — fixture, no un secreto
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
BERNARD = "907264175246569543"
AUTH0_SUB = "google-oauth2|118273645509"


class FakeConn:
    """Una tabla `principal_identities` en RAM con la forma de las dos queries del módulo."""

    def __init__(self, rows: list[tuple[str, str, str]] | None = None, *, fail: bool = False) -> None:
        self.rows = rows or []  # (surface, external_id, principal_id)
        self.fail = fail
        self.ddl_runs = 0

    async def execute(self, sql: str, *args):
        if self.fail:
            raise RuntimeError("pg down")
        if "CREATE TABLE" in sql:
            self.ddl_runs += 1

    async def fetch(self, sql: str, *args):
        if self.fail:
            raise RuntimeError("pg down")
        if "surface = $1 AND external_id = $2" in sql:
            surface, ext = args
            hits = [r for r in self.rows if r[0] == surface and r[1] == ext]
        else:
            (ext,) = args
            hits = [r for r in self.rows if r[1] == ext]
        return [{"surface": s, "principal_id": p} for s, _e, p in hits]


def _install(monkeypatch, conn: FakeConn | None) -> None:
    @asynccontextmanager
    async def acquire():
        yield conn

    monkeypatch.setattr(principal_identity.shared, "acquire", acquire)
    monkeypatch.setattr(principal_identity, "_ddl_applied", False)


# --- resolve() ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_linked_auth0_sub_resolves_to_the_snowflake_with_surface(monkeypatch):
    _install(monkeypatch, FakeConn([("og118", AUTH0_SUB, BERNARD)]))
    assert await principal_identity.resolve(AUTH0_SUB, "og118") == BERNARD


@pytest.mark.asyncio
async def test_without_surface_a_unique_match_still_resolves(monkeypatch):
    # og118 hoy no manda `surface`; el id de Auth0 es único entre superficies.
    _install(monkeypatch, FakeConn([("og118", AUTH0_SUB, BERNARD)]))
    assert await principal_identity.resolve(AUTH0_SUB, None) == BERNARD


@pytest.mark.asyncio
async def test_the_same_external_id_on_two_surfaces_is_a_collision_not_an_identity(monkeypatch):
    _install(monkeypatch, FakeConn([("telegram", "12345", BERNARD), ("whatsapp", "12345", "111111111111111111")]))
    assert await principal_identity.resolve("12345", None) == "12345"
    # Con superficie la ambigüedad desaparece.
    assert await principal_identity.resolve("12345", "telegram") == BERNARD


@pytest.mark.asyncio
async def test_an_unlinked_id_passes_through_unchanged(monkeypatch):
    _install(monkeypatch, FakeConn([]))
    assert await principal_identity.resolve(BERNARD, "discord") == BERNARD
    assert await principal_identity.resolve(AUTH0_SUB, "og118") == AUTH0_SUB


@pytest.mark.asyncio
async def test_no_postgres_or_a_failing_query_degrades_to_no_bridge(monkeypatch):
    _install(monkeypatch, None)
    assert await principal_identity.resolve(AUTH0_SUB, "og118") == AUTH0_SUB
    _install(monkeypatch, FakeConn(fail=True))
    assert await principal_identity.resolve(AUTH0_SUB, "og118") == AUTH0_SUB


@pytest.mark.asyncio
async def test_ddl_is_applied_once_per_process(monkeypatch):
    conn = FakeConn([])
    _install(monkeypatch, conn)
    await principal_identity.resolve("a", None)
    await principal_identity.resolve("b", None)
    assert conn.ddl_runs == 1


def test_snowflake_shape():
    assert principal_identity.looks_like_snowflake(BERNARD)
    assert not principal_identity.looks_like_snowflake(AUTH0_SUB)
    assert not principal_identity.looks_like_snowflake("12345")


# --- la puerta del runner -----------------------------------------------------


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("persona_runner.core.config.RUNNER_AUTH_TOKEN", TOKEN)
    turn_jobs.JOBS.clear()
    app = FastAPI()
    app.include_router(turn_api.router)
    with TestClient(app) as c:
        yield c
    turn_jobs.JOBS.clear()


def _capture_turn(monkeypatch) -> list[TurnRequest]:
    seen: list[TurnRequest] = []

    async def fake_turn(req: TurnRequest) -> TurnResponse:
        seen.append(req)
        return TurnResponse(text="ok")

    monkeypatch.setattr(aire_route, "turn_via_aire", fake_turn)
    return seen


def test_sync_turn_reaches_aire_with_the_canonical_principal(client, monkeypatch):
    _install(monkeypatch, FakeConn([("og118", AUTH0_SUB, BERNARD)]))
    seen = _capture_turn(monkeypatch)
    body = {
        "channel_id": "conv-1",
        "user_id": AUTH0_SUB,
        "user_text": "hola",
        "persona_id": "insult",
        "surface": "og118",
    }
    assert client.post("/v1/turn", json=body, headers=HEADERS).status_code == 200
    assert seen[0].user_id == BERNARD
    assert seen[0].surface == "og118"


def test_job_turn_is_persisted_already_resolved(client, monkeypatch):
    _install(monkeypatch, FakeConn([("og118", AUTH0_SUB, BERNARD)]))
    seen = _capture_turn(monkeypatch)
    body = {"channel_id": "conv-1", "user_id": AUTH0_SUB, "user_text": "hola", "persona_id": "insult"}
    r = client.post("/v1/turn/jobs", json=body, headers=HEADERS)
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    done = client.get(f"/v1/turn/jobs/{job_id}", params={"wait_s": 5}, headers=HEADERS).json()
    assert done["status"] == "done"
    assert seen[0].user_id == BERNARD


def test_discord_callers_are_untouched(client, monkeypatch):
    _install(monkeypatch, FakeConn([]))
    seen = _capture_turn(monkeypatch)
    body = {"channel_id": "1489180895264116736", "user_id": BERNARD, "user_text": "hola", "persona_id": "vultur"}
    assert client.post("/v1/turn", json=body, headers=HEADERS).status_code == 200
    assert seen[0].user_id == BERNARD
    assert seen[0].surface is None


def test_surface_must_be_a_plain_slug(client):
    body = {"channel_id": "c", "user_id": BERNARD, "user_text": "hola", "surface": "OG 118"}
    assert client.post("/v1/turn", json=body, headers=HEADERS).status_code == 422
