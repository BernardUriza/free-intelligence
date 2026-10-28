"""Runtime personas (OG118-ELEMENTOS-ALTA, 2026-10-28) — a persona born without a deploy.

Positive: a PUT lands a version, the next turn's resolution finds its DNA file and
its engine (Codex pinned to its model), and a fresh replica rebuilds both from the
store. Resistance: an id the image owns (insult, astra) is refused, a bad id or a
Codex persona without a model is a 422, and no token is a 401 before any write.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from persona_core.memory.repositories.runtime_personas import RuntimePersonaRow
from persona_runner.api import personas as personas_api
from persona_runner.engine import aire_route, persona_files, runtime_personas

ROOT = Path(__file__).parents[2]
TOKEN = "tok-1"  # noqa: S105 — fixture, not a secret
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
DNA = "Eres Radón. Hablas de gases nobles y de nada más."


class FakeRepo:
    def __init__(self):
        self.rows: list[RuntimePersonaRow] = []

    async def append(self, *, persona_id, display_name, provider, model, dna, created_by):
        version = len(self.rows) + 1
        self.rows.append(RuntimePersonaRow(persona_id, display_name, provider, model, dna, version))
        return version

    async def latest(self):
        newest: dict[str, RuntimePersonaRow] = {}
        for row in self.rows:
            newest[row.persona_id] = row
        return list(newest.values())


class FakeMemory:
    def __init__(self, repo):
        self.runtime_personas = repo


@pytest.fixture
def store(monkeypatch, tmp_path):
    monkeypatch.setattr("persona_runner.core.config.PERSONAS_DIR", ROOT / "shared" / "personas")
    monkeypatch.setattr("persona_runner.core.config.RUNTIME_PERSONAS_DIR", tmp_path / "runtime")
    monkeypatch.setattr("persona_runner.core.config.RUNNER_AUTH_TOKEN", TOKEN)
    monkeypatch.setattr(runtime_personas, "_RUNTIME", {})
    repo = FakeRepo()

    async def get_memory():
        return FakeMemory(repo)

    monkeypatch.setattr(personas_api, "get_memory", get_memory)
    app = FastAPI()
    app.include_router(personas_api.router)
    with TestClient(app) as client:
        yield client, repo


def put(client, persona_id, **body):
    payload = {"display_name": "Radón", "dna": DNA} | body
    return client.put(f"/v1/personas/{persona_id}", json=payload, headers=HEADERS)


def test_a_written_persona_serves_the_next_turn_on_its_engine(store):
    client, _ = store
    r = put(client, "radon", provider="codex", model="gpt-6-astra")
    assert r.status_code == 200
    assert r.json() == {"persona_id": "radon", "version": 1, "provider": "codex", "model": "gpt-6-astra"}

    assert persona_files.load_persona("radon") == DNA
    assert aire_route.base_persona_id("radon") == "radon"
    assert aire_route.engine_for("radon") == ("codex", "gpt-6-astra")


def test_a_claude_persona_keeps_the_router_and_drops_a_stray_model(store):
    client, _ = store
    r = put(client, "radon", provider="claude", model="claude-opus-4-7")
    assert r.status_code == 200
    assert r.json()["model"] is None
    assert aire_route.engine_for("radon") == ("claude", None)


def test_an_edit_is_a_new_version_and_the_newest_wins(store):
    client, repo = store
    put(client, "radon")
    r = put(client, "radon", dna="Eres Radón, segunda versión.")
    assert r.json()["version"] == 2
    assert len(repo.rows) == 2
    assert persona_files.load_persona("radon") == "Eres Radón, segunda versión."


async def test_a_fresh_replica_rebuilds_from_the_store(store, monkeypatch):
    client, repo = store
    put(client, "radon", provider="codex", model="gpt-6-astra")
    monkeypatch.setattr(runtime_personas, "_RUNTIME", {})
    assert aire_route.base_persona_id("radon") == "insult"

    assert await runtime_personas.hydrate(repo) == 1
    assert persona_files.load_persona("radon") == DNA
    assert aire_route.engine_for("radon") == ("codex", "gpt-6-astra")


@pytest.mark.parametrize("persona_id", ["insult", "astra", "vultur"])
def test_an_image_persona_cannot_be_rewritten(store, persona_id):
    client, repo = store
    r = put(client, persona_id)
    assert r.status_code == 422
    assert repo.rows == []
    assert runtime_personas.lookup(persona_id) is None


@pytest.mark.parametrize(
    ("persona_id", "body"),
    [
        ("Radon", {}),
        ("radon-x", {}),
        ("radon", {"provider": "codex"}),
        ("radon", {"provider": "gemini", "model": "x"}),
        ("radon", {"dna": "   "}),
    ],
)
def test_an_invalid_write_is_refused_before_the_store(store, persona_id, body):
    client, repo = store
    r = put(client, persona_id, **body)
    assert r.status_code == 422
    assert repo.rows == []


def test_no_token_writes_nothing(store):
    client, repo = store
    r = client.put("/v1/personas/radon", json={"display_name": "Radón", "dna": DNA})
    assert r.status_code == 401
    assert repo.rows == []
