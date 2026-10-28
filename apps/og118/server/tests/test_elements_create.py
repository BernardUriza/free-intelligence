"""OG118-ELEMENTOS-ALTA (2026-10-28) — an element is born from the UI, with no deploy.

Positive: an author claims an empty slot, the persona goes to the engine FIRST, and
the slot shows up in `GET /elements` and resolves on the next turn — including on a
fresh process that only has the overlay on the volume. Resistance: a non-author, the
legacy bearer and an unset allowlist write nothing; a taken slot, a stolen alias or
an engine refusal leaves the catalog untouched.
"""

from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

import app as app_module
import elements_registry
from external_engine import PersonaWriteError

AUTHOR = "auth0|bernard"
AUTHOR_HASH = hashlib.sha256(AUTHOR.encode("utf-8")).hexdigest()[:32]
BODY = {
    "atomicNumber": 86,
    "displayName": "Radón",
    "personaId": "radon",
    "description": "Gases nobles, sin más.",
    "aliases": ["Rn-Bot"],
    "provider": "codex",
    "model": "gpt-6-astra",
    "dna": "Eres Radón.",
}


@pytest.fixture
def engine(monkeypatch, tmp_path):
    overlay = tmp_path / "elements.overlay.json"
    monkeypatch.setenv("OG118_ELEMENTS_OVERLAY_PATH", str(overlay))
    monkeypatch.setenv("OG118_ELEMENT_AUTHORS", AUTHOR_HASH)
    elements_registry.get_registry.cache_clear()
    calls: list[tuple[str, dict]] = []

    async def fake_put(persona_id, body):
        calls.append((persona_id, body))
        return {"persona_id": persona_id, "version": 7, "provider": body["provider"], "model": body["model"]}

    monkeypatch.setattr(app_module, "put_persona", fake_put)
    yield calls, overlay
    elements_registry.get_registry.cache_clear()


@pytest.fixture
def client(as_account) -> TestClient:
    as_account(AUTHOR)
    return TestClient(app_module.app)


def active_slugs(client) -> set[str]:
    return {e["slug"] for e in client.get("/elements").json()["elements"]}


def test_an_author_claims_an_empty_slot_and_it_serves_at_once(client, engine):
    calls, overlay = engine
    assert "radon" not in active_slugs(client)

    r = client.post("/elements", json=BODY)
    assert r.status_code == 201, r.text
    assert r.json()["id"] == "element-086-rn-radon"
    assert r.json()["personaVersion"] == 7
    assert calls == [
        ("radon", {"display_name": "Radón", "provider": "codex", "model": "gpt-6-astra",
                   "dna": "Eres Radón.", "created_by": AUTHOR_HASH})
    ]

    assert "radon" in active_slugs(client)
    el = elements_registry.get_registry().resolve("rn-bot")
    assert el.atomic_number == 86 and el.engine_binding.persona_id == "radon"
    assert json.loads(overlay.read_text())["claims"][0]["personaId"] == "radon"


def test_a_fresh_process_rebuilds_the_claim_from_the_volume(client, engine):
    client.post("/elements", json=BODY)
    elements_registry.get_registry.cache_clear()
    el = elements_registry.get_registry().resolve("radon")
    assert el is not None and el.is_active and el.engine_binding.persona_id == "radon"


def test_the_slot_list_names_only_empty_slots_and_the_author_bit(client, engine):
    body = client.get("/elements/slots").json()
    assert body["canCreate"] is True
    zs = {s["atomicNumber"] for s in body["slots"]}
    assert 86 in zs and 85 not in zs and 8 not in zs


@pytest.mark.parametrize("sub", ["auth0|somebody-else"])
def test_a_non_author_writes_nothing(client, engine, as_account, sub):
    calls, overlay = engine
    as_account(sub)
    assert client.get("/elements/slots").json()["canCreate"] is False
    r = client.post("/elements", json=BODY)
    assert r.status_code == 403
    assert calls == [] and not overlay.exists()


def test_an_unset_allowlist_closes_the_door(client, engine, monkeypatch):
    calls, overlay = engine
    monkeypatch.delenv("OG118_ELEMENT_AUTHORS")
    assert client.post("/elements", json=BODY).status_code == 403
    assert calls == [] and not overlay.exists()


@pytest.mark.parametrize(
    "change",
    [
        {"atomicNumber": 85},
        {"atomicNumber": 8},
        {"aliases": ["oxigeno"]},
    ],
)
def test_a_taken_slot_or_alias_is_refused_before_the_engine(client, engine, change):
    calls, overlay = engine
    r = client.post("/elements", json=BODY | change)
    assert r.status_code == 409
    assert calls == [] and not overlay.exists()


def test_an_engine_refusal_leaves_the_catalog_untouched(client, engine, monkeypatch):
    _, overlay = engine

    async def refuse(persona_id, body):
        raise PersonaWriteError(422, "persona_id 'radon' belongs to the image")

    monkeypatch.setattr(app_module, "put_persona", refuse)
    r = client.post("/elements", json=BODY)
    assert r.status_code == 422
    assert not overlay.exists()
    assert "radon" not in active_slugs(client)


def test_a_second_claim_on_the_same_slot_is_refused(client, engine):
    assert client.post("/elements", json=BODY).status_code == 201
    r = client.post("/elements", json=BODY | {"personaId": "radon_two", "aliases": []})
    assert r.status_code == 409
