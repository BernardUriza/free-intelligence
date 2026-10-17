"""Every frame /chat/stream emits validates against the fi-runner stream contract.

`contracts/agent-events.schema.json` is what the web (wire.generated.ts) and the
iPhone (WireEvent.generated.swift) are generated from. A field this server puts
on the wire that the schema does not declare reaches the web only by hand and
never reaches the phone: `reactions` rode the `result` frame for weeks that way,
and a reaction-only turn showed on iOS as "frames without text". This test is
the gate the rail was missing: the server's wire IS the contract, frame by frame.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import app as app_module
import external_engine
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

CONTRATO = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "fi-runner"
    / "contracts"
    / "agent-events.schema.json"
)


@pytest.fixture(scope="module")
def validador() -> Draft202012Validator:
    schema = json.loads(CONTRATO.read_text("utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _frames(body: str) -> list[dict]:
    frames = []
    for bloque in body.split("\n\n"):
        for linea in bloque.split("\n"):
            if linea.startswith("data:"):
                frames.append(json.loads(linea[5:].strip()))
    return frames


class _Runner:
    def __init__(self, eventos: list[dict]) -> None:
        self.eventos = eventos

    async def run_stream(self, message, **_) -> AsyncIterator[dict]:  # noqa: ANN001
        for e in self.eventos:
            yield e


def _errores(validador: Draft202012Validator, frame: dict) -> list[str]:
    return [e.message for e in validador.iter_errors(frame)]


def test_a_reaction_only_turn_is_on_the_contract(monkeypatch, validador) -> None:
    monkeypatch.setattr(
        app_module,
        "_runner",
        _Runner([{"type": "result", "result": {"text": "", "reactions": ["🔥", "👀"]}}]),
    )
    resp = TestClient(app_module.app).post("/chat/stream", json={"message": "mira"})
    assert resp.status_code == 200

    frames = _frames(resp.text)
    assert [f["type"] for f in frames] == ["open", "result", "done"]
    for frame in frames:
        assert _errores(validador, frame) == [], frame
    assert frames[1]["result"]["reactions"] == ["🔥", "👀"]


def test_the_external_engine_turn_is_on_the_contract(validador) -> None:
    turno = {"text": "hola", "model": "claude-sonnet-4-6", "reactions": ["🔥"], "gif_urls": []}
    for evento in external_engine.outbound_events(turno):
        assert _errores(validador, evento) == [], evento

    vacio = external_engine.outbound_events({"text": "", "reactions": [], "empty_reason": "brain_empty"})
    assert [e["type"] for e in vacio] == ["error"]
    assert _errores(validador, vacio[0]) == []


def test_the_contract_rejects_what_the_server_must_not_send(validador) -> None:
    colado = {"type": "result", "result": {"text": "x", "mood": "happy"}}
    assert _errores(validador, colado) != [], "un campo fuera del contrato debe fallar aquí, no en el teléfono"
