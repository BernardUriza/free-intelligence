"""El servidor guarda lo que el contrato declara — probado contra el schema.

`ConversationRecordRequest` tipa `messages: list[dict]`, o sea que hoy acepta
CUALQUIER cosa dentro de un mensaje. Eso es lo que permitió que el iPhone
subiera `author` como string suelto durante semanas sin que nada se quejara,
y que la web y el teléfono divergieran en silencio.

Este test no cambia el runtime: ata el modelo del servidor al mismo
`conversation-record.schema.json` del que derivan TypeScript y Swift, para que
un cambio de contrato rompa aquí en vez de romper en el teléfono de alguien.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

CONTRATO = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "free-intelligence-core"
    / "contracts"
    / "conversation-record.schema.json"
)


@pytest.fixture(scope="module")
def validador() -> Draft202012Validator:
    schema = json.loads(CONTRATO.read_text("utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _record(**extra) -> dict:
    base = {
        "id": "c1",
        "title": "hola",
        "createdAt": "2026-08-13T10:00:00Z",
        "updatedAt": "2026-08-13T10:00:00Z",
        "messages": [{"role": "user", "content": "hola"}],
        "preview": "hola",
        "schemaVersion": 1,
    }
    base.update(extra)
    return base


def test_el_contrato_acepta_un_record_minimo(validador):
    assert list(validador.iter_errors(_record())) == []


def test_el_contrato_acepta_lo_que_la_web_escribe(validador):
    """Autoría, imágenes y trace: lo que el teléfono borraba al re-guardar."""
    completo = _record(
        messages=[
            {
                "role": "user",
                "content": "mira",
                "images": [{"mediaType": "image/png", "data": "QUJD"}],
            },
            {
                "role": "assistant",
                "content": "la veo",
                "author": {"id": "53", "name": "Yodo", "symbol": "I"},
                "trace": {
                    "plan": {"steps": [{"label": "mirar", "status": "done"}]},
                    "tools": [{"name": "read", "server": "fs", "isError": False}],
                    "model": "claude-sonnet-4-5",
                },
            },
        ]
    )
    assert list(validador.iter_errors(completo)) == []


def test_el_autor_como_string_suelto_es_INVALIDO(validador):
    """La forma que el iPhone subió durante semanas. El contrato la rechaza."""
    malo = _record(messages=[{"role": "assistant", "content": "hola", "author": "Yodo"}])
    errores = list(validador.iter_errors(malo))
    assert errores, "el contrato debe rechazar un autor que no sea objeto"


def test_un_rol_inventado_es_INVALIDO(validador):
    malo = _record(messages=[{"role": "system", "content": "hola"}])
    assert list(validador.iter_errors(malo))


def test_el_modelo_del_servidor_acepta_lo_que_el_contrato_acepta():
    """Guarda que el pydantic no se quede corto respecto al contrato."""
    from app import ConversationRecordRequest  # noqa: PLC0415

    modelo = ConversationRecordRequest(**_record())
    assert modelo.messages == [{"role": "user", "content": "hola"}]
