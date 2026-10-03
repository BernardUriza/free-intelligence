"""Romper el registro a propósito NO puede costar el turno (issue #54).

El criterio de aceptación no se conforma con "el registro está en un try": pide
un test que **rompa el registro a propósito y verifique que el turno se
completa**. Eso es lo que hace este archivo, por cada una de las dos cosas que
pueden caerse — el veredicto de fi-core y el registro mismo. (Hasta v4.38.17
eran tres: la lectura de señales era una llamada aparte; desde fi-core 0.30.0
viaja dentro del mismo `ClinicalVerdict` que la banda.)

Por qué importa más de lo que parece: el turno que se pierde aquí no es un
turno cualquiera. `build_turn_guidance` es la costura por donde viaja el
overlay de persona vulnerable (`tests/core/test_presets_clinical.py`), así que
un registro que tumba el guidance le quita su protección justo a quien la
necesita, y por una razón tan tonta como un log atragantado.

Estos tests importan fi-core, así que corren en CI. Los que verifican el
contenido de los eventos —el seudónimo, el recorte, el hash— viven en
`test_audit_pseudonym.py`, `test_crisis_band_events.py` y `test_audit_hash.py`,
que corren en cualquier máquina a propósito.
"""

from __future__ import annotations

import pytest
from structlog.testing import capture_logs

from persona_core.guidance import build_turn_guidance

MENSAJE_GRAVE = "tengo un plan suicida"
FACTS_CON_INTENTO = [{"fact": "tuvo un intento de suicidio el año pasado"}]


def truena(*_args, **_kwargs):
    raise RuntimeError("roto a propósito")


def construir():
    """Un turno completo. Devuelve (guidance, eventos capturados)."""
    with capture_logs() as capturado:
        guidance = build_turn_guidance(
            current_message=MENSAJE_GRAVE,
            recent_messages=[],
            user_facts=FACTS_CON_INTENTO,
            persona_id="insult",
            user_id="284712993456127001",
        )
    return guidance, capturado


def eventos(capturado, nombre):
    return [e for e in capturado if e["event"] == nombre]


# ---------------------------------------------------------------------------
# El control — sin esto, los tests de abajo pasarían por vacuidad
# ---------------------------------------------------------------------------


def test_sin_romper_nada_hay_guidance_y_hay_veredicto():
    """El caso sano: el turno sale Y el veredicto se registra."""
    guidance, capturado = construir()
    assert guidance
    assert len(eventos(capturado, "crisis_band_classified")) == 1
    assert not eventos(capturado, "crisis_band_absent")


# ---------------------------------------------------------------------------
# Romperlo a propósito, una pieza a la vez
# ---------------------------------------------------------------------------


def test_si_el_clasificador_truena_el_turno_se_completa(monkeypatch):
    """fi-core caído: se pierde la banda, no la respuesta que alguien espera."""
    monkeypatch.setattr("persona_core.guidance.crisis_verdict", truena)
    guidance, capturado = construir()
    assert guidance, "el turno se perdió por una falla del clasificador"
    assert not eventos(capturado, "crisis_band_classified")
    assert eventos(capturado, "crisis_band_absent")[0]["reason"] == "crisis_band_failed"


def test_el_veredicto_registrado_no_lleva_una_frase_del_vocabulario():
    """La decisión 1 de Álex, cerrada río arriba (fi-core 0.30.0): `reasons` va
    como `kind:key:peso`, y `signals` como nombres de grupo. Ni una palabra del
    mensaje ni una frase de PSYCHIATRY en el renglón."""
    _, capturado = construir()
    (evento,) = eventos(capturado, "crisis_band_classified")
    assert evento["reasons"] == ["critical_pattern:critical_patterns:+10"]
    assert evento["signals"] == ["explicit_ideation"]
    assert MENSAJE_GRAVE not in str(evento)
    assert "plan suicida" not in str(evento)


def test_si_el_registro_truena_el_turno_se_completa(monkeypatch):
    """La falla que el issue nombra por su nombre: "un serializador que se atraganta"."""
    monkeypatch.setattr("persona_core.guidance.log_crisis_band_classified", truena)
    guidance, capturado = construir()
    assert guidance, "el turno se perdió por una falla del REGISTRO"
    # Y el denominador no miente sobre qué se cayó: hubo veredicto, falló el log.
    assert eventos(capturado, "crisis_band_absent")[0]["reason"] == "crisis_band_log_failed"


def test_el_overlay_del_guardian_sobrevive_al_registro_roto(monkeypatch):
    """Lo que de verdad está en juego: la protección de quien la necesita.

    No basta con que vuelva "algún" guidance — tiene que volver el MISMO que
    sin la falla, overlay incluido.
    """
    sano, _ = construir()
    monkeypatch.setattr("persona_core.guidance.log_crisis_band_classified", truena)
    con_registro_roto, _ = construir()
    assert con_registro_roto == sano


# ---------------------------------------------------------------------------
# El denominador, por el camino que no pasa por la banda
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mensaje", ["", "   ", "\n"])
def test_un_mensaje_vacio_tambien_cuenta_en_el_denominador(mensaje):
    """Sin esto, los turnos que salen temprano son invisibles y la tasa miente."""
    with capture_logs() as capturado:
        assert (
            build_turn_guidance(
                current_message=mensaje,
                recent_messages=[],
                user_facts=None,
                persona_id="insult",
            )
            is None
        )
    assert eventos(capturado, "crisis_band_absent")[0]["reason"] == "mensaje_vacio"
