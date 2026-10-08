"""Los dos eventos del veredicto de banda (issue #54).

El par `crisis_band_classified` / `crisis_band_absent` existe por la lección
fundadora de `.claude/rules/router-observability.md`: un contador solo, sin
denominador, tiene la forma exacta de `recovered_without_context` — su cero se
lee como salud cuando en realidad puede significar "esta rama ya no puede
sonar". Aquí se fija que los dos suben por caminos distintos y que el veredicto
lleva lo que Álex decidió que lleve, ni una palabra más.

Estos tests corren SIN fi-core instalado a propósito: `persona_core.audit`
no importa `behavior`, así que la máquina de Álex puede verificar la parte que
guarda datos de personas reales sin depender del entorno de Bernard.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from structlog.testing import capture_logs

from persona_core.audit import (
    ABSENT_EVENT,
    AUDIT_KEY_ENV,
    CLASSIFIED_EVENT,
    MAX_REASONS,
    log_crisis_band_absent,
    log_crisis_band_classified,
)

UNA_PERSONA = "284712993456127001"
SEPTIEMBRE = datetime(2026, 9, 8, 15, 20, tzinfo=UTC)


@pytest.fixture
def con_llave(monkeypatch):
    monkeypatch.setenv(AUDIT_KEY_ENV, "llave-de-prueba-no-es-la-de-produccion")


def clasificar(**cambios):
    """Emite un veredicto y devuelve el evento capturado."""
    campos = {
        "band": "HIGH",
        "gravity": 7.0,
        "reasons": ["ideación suicida pasiva"],
        "critical_override": False,
        "signals": ["explicit_ideation"],
        "persona_id": "valentis",
        "user_id": UNA_PERSONA,
        "now": SEPTIEMBRE,
    }
    campos.update(cambios)
    with capture_logs() as capturado:
        log_crisis_band_classified(**campos)
    # Se filtra por nombre: sin llave sale además el aviso `crisis_audit_key_missing`.
    veredictos = [e for e in capturado if e["event"] == CLASSIFIED_EVENT]
    assert len(veredictos) == 1
    return veredictos[0]


# ---------------------------------------------------------------------------
# El veredicto — qué lleva y qué NO lleva
# ---------------------------------------------------------------------------


def test_el_veredicto_sale_con_su_nombre_estable(con_llave):
    """El evento tiene nombre propio: ya no vive escondido en `guidance_built`."""
    evento = clasificar()
    assert evento["event"] == CLASSIFIED_EVENT
    assert evento["band"] == "HIGH"
    assert evento["gravity"] == 7.0
    assert evento["persona_id"] == "valentis"


def test_las_senales_van_por_nombre_de_grupo_no_por_texto(con_llave):
    """Decisión 1: se explica el veredicto sin volcar una palabra de la persona."""
    evento = clasificar(signals=["explicit_ideation", "at_the_limit"])
    assert evento["signals"] == ["explicit_ideation", "at_the_limit"]
    # El texto del turno no viaja: el evento no tiene dónde meterlo.
    assert "current_message" not in evento
    assert "message" not in evento


def test_las_reasons_se_recortan_a_tres(con_llave):
    """Decisión 2: 3, que es lo que ya corre en observación y ya está medido."""
    evento = clasificar(reasons=[f"razón {n}" for n in range(10)])
    assert len(evento["reasons"]) == MAX_REASONS == 3
    assert evento["reasons"] == ["razón 0", "razón 1", "razón 2"]


# ---------------------------------------------------------------------------
# El apodo — sólo en los graves (decisión de Álex, 2026-09-08)
# ---------------------------------------------------------------------------


def test_un_turno_low_se_registra_pero_sin_apodo(con_llave):
    """El denominador necesita el renglón; el renglón no necesita a la persona."""
    evento = clasificar(band="LOW", gravity=0.0, signals=[])
    assert evento["event"] == CLASSIFIED_EVENT
    assert evento["band"] == "LOW"
    assert evento["user_id"] is None


@pytest.mark.parametrize("banda", ["MEDIUM", "HIGH", "CRITICAL"])
def test_un_turno_grave_si_lleva_apodo(con_llave, banda):
    evento = clasificar(band=banda)
    assert evento["user_id"] == "2026-09:" + evento["user_id"].split(":")[1]
    assert evento["user_id"].startswith("2026-09:")


def test_el_apodo_no_es_el_user_id(con_llave):
    """Lo obvio, fijado: el identificador de Discord no llega al log."""
    evento = clasificar()
    assert UNA_PERSONA not in str(evento)


def test_sin_llave_el_turno_grave_se_registra_sin_apodo(monkeypatch):
    """La condición dura, ya del lado del evento: se pierde el apodo, no el renglón."""
    monkeypatch.delenv(AUDIT_KEY_ENV, raising=False)
    evento = clasificar(band="CRITICAL")
    assert evento["band"] == "CRITICAL"
    assert evento["user_id"] is None


# ---------------------------------------------------------------------------
# El denominador
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "motivo",
    ["mensaje_vacio", "sin_guidance", "crisis_band_failed", "guidance_build_failed"],
)
def test_el_denominador_dice_por_que_no_hubo_veredicto(motivo):
    """ "No había nada que clasificar" y "el detector se cayó" no son lo mismo."""
    with capture_logs() as capturado:
        log_crisis_band_absent(persona_id="valentis", reason=motivo)
    assert len(capturado) == 1
    assert capturado[0]["event"] == ABSENT_EVENT
    assert capturado[0]["reason"] == motivo
    # Sin veredicto no sabemos si el turno era grave, así que no se marca a nadie.
    assert capturado[0]["user_id"] is None


# ---------------------------------------------------------------------------
# La regla dura: el registro no puede matar el turno
# ---------------------------------------------------------------------------


def test_una_falla_al_emitir_no_revienta(monkeypatch, con_llave):
    """Si Log Analytics o el serializador truenan, se pierde la métrica. Nada más."""

    class LoggerQueTruena:
        def __init__(self):
            self.exceptions: list[str] = []

        def info(self, *_args, **_kwargs):
            raise RuntimeError("el serializador se atragantó")

        def exception(self, event, **_kwargs):
            self.exceptions.append(event)

    falso = LoggerQueTruena()
    monkeypatch.setattr("persona_core.audit.log", falso)

    log_crisis_band_absent(persona_id="valentis", reason="mensaje_vacio")
    log_crisis_band_classified(
        band="CRITICAL",
        gravity=10.0,
        reasons=["plan suicida"],
        critical_override=True,
        signals=["explicit_ideation"],
        persona_id="valentis",
        user_id=UNA_PERSONA,
        now=SEPTIEMBRE,
    )

    assert falso.exceptions == ["crisis_audit_emit_failed"] * 2
