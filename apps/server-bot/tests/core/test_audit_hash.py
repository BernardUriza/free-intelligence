"""El `audit_hash` de los eventos de banda (issue #54).

La disciplina que se porta del patrón `DomainEvent` de fi-core no es su
infraestructura —este repo NO construye un event store, structlog + Log
Analytics ya existen— sino su forma: nombre estable, campos tipados y **un hash
que prueba que el renglón no se editó después**. Un veredicto sobre una persona
en crisis que se puede reescribir a posteriori no es un registro auditable.

El reparto de los tests de este archivo es a propósito:

- Los que verifican la FORMA del payload corren en cualquier máquina, con un
  doble de `sha256_payload` — así la parte que decide qué se guarda de personas
  reales se puede verificar sin fi-core instalado.
- El que verifica que el hash REAL sale corre sólo donde fi-core existe (CI).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from structlog.testing import capture_logs

from persona_core.audit import log_crisis_band_absent, log_crisis_band_classified

SEPTIEMBRE = datetime(2026, 9, 8, 15, 20, tzinfo=UTC)


def un_veredicto(**cambios):
    campos = {
        "band": "HIGH",
        "gravity": 7.0,
        "reasons": ["ideación suicida pasiva"],
        "critical_override": False,
        "signals": ["explicit_ideation"],
        "persona_id": "valentis",
        "user_id": "284712993456127001",
        "now": SEPTIEMBRE,
    }
    campos.update(cambios)
    with capture_logs() as capturado:
        log_crisis_band_classified(**campos)
    return next(e for e in capturado if e["event"] == "crisis_band_classified")


# ---------------------------------------------------------------------------
# La forma del payload — verificable sin fi-core
# ---------------------------------------------------------------------------


@pytest.fixture
def payloads_vistos(monkeypatch):
    """Un doble de `sha256_payload` que guarda lo que le dieron a hashear."""
    vistos: list[dict] = []

    def espia(payload):
        vistos.append(dict(payload))
        return "hash-de-mentiras"

    monkeypatch.setenv("CRISIS_AUDIT_KEY", "llave-de-prueba")
    monkeypatch.setattr("persona_core.audit.sha256_payload", espia)
    return vistos


def test_el_hash_cubre_el_nombre_del_evento(payloads_vistos):
    """Sin esto, un `absent` podría reetiquetarse como veredicto y el hash cuadraría."""
    un_veredicto()
    assert payloads_vistos[0]["event"] == "crisis_band_classified"


def test_el_hash_cubre_todo_lo_que_sale_en_el_evento(payloads_vistos):
    """Lo hasheado y lo emitido son el MISMO conjunto de campos, no dos primos."""
    evento = un_veredicto()
    emitido = {k: v for k, v in evento.items() if k not in ("audit_hash", "log_level")}
    assert payloads_vistos[0] == emitido


def test_el_denominador_tambien_lleva_hash(payloads_vistos):
    """Un denominador manipulable es tan malo como un veredicto manipulable."""
    with capture_logs() as capturado:
        log_crisis_band_absent(persona_id="valentis", reason="crisis_band_failed")
    assert capturado[0]["audit_hash"] == "hash-de-mentiras"
    assert payloads_vistos[0]["event"] == "crisis_band_absent"


def test_dos_veredictos_distintos_no_comparten_payload(payloads_vistos):
    """El hash sirve de algo sólo si el payload cambia cuando el veredicto cambia."""
    un_veredicto(band="HIGH")
    un_veredicto(band="CRITICAL")
    assert payloads_vistos[0] != payloads_vistos[1]


# ---------------------------------------------------------------------------
# Fail-safe — el hash es lo primero que se sacrifica, nunca el turno
# ---------------------------------------------------------------------------


def test_sin_fi_core_el_evento_sale_igual_sin_hash(monkeypatch):
    """La máquina de Álex, y cualquier entorno donde falte el paquete."""
    monkeypatch.setattr("persona_core.audit.sha256_payload", None)
    assert un_veredicto()["audit_hash"] is None


def test_si_el_hash_truena_el_evento_sale_igual(monkeypatch):
    """Un renglón sin hash sigue siendo mejor que un turno perdido."""

    def truena(_payload):
        raise RuntimeError("el payload traía algo no serializable")

    monkeypatch.setattr("persona_core.audit.sha256_payload", truena)
    assert un_veredicto()["audit_hash"] is None


# ---------------------------------------------------------------------------
# El hash de verdad — sólo donde fi-core vive (CI)
# ---------------------------------------------------------------------------


def test_con_fi_core_el_hash_es_real_y_estable():
    """`sha256_payload` de fi-core, no un `hashlib.sha256` escrito a mano."""
    pytest.importorskip("fi_core.cognitive", reason="fi-core no está en esta máquina")
    primero = un_veredicto()["audit_hash"]
    assert isinstance(primero, str) and primero
    # Mismo payload → mismo hash (si no, no prueba nada).
    assert un_veredicto()["audit_hash"] == primero
    # Payload distinto → hash distinto (si no, tampoco prueba nada).
    assert un_veredicto(band="CRITICAL")["audit_hash"] != primero
