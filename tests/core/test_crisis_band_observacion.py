"""La crisis deja de ser un booleano y pasa a ser una banda (issue #53, PR 1 de 2).

Este PR corre en **MODO OBSERVACIÓN**, decisión de Álex del 2026-09-01 y
ratificada el 2026-09-03 ya con fi-core 0.27.0: la banda se calcula y se
registra, y **no cambia lo que una persona lee**. La razón está medida y vive en
`test_el_defecto_de_sin_medido_tras_fi_core_0_27_0` — 0.27.0 arregló "mejor sin
mí" pero no "sin esperanza", así que encender la banda hoy seguiría haciendo
PERDER detección que hoy funciona.

Regla del mutador, la misma del #52: positivo (la tabla del issue da lo que
promete) + resistencia (los defectos de fi-core declarados uno por uno, no
escondidos) + guardián (el reloj de urgencias NUNCA le llega a una persona).
"""

from __future__ import annotations

import pytest
from fi_core.cognitive import URGENCY_BANDS

from khimeras_shared.behavior.vulnerability import (
    crisis_band,
    history_conditions,
    is_acute_crisis,
    symptoms_in_message,
)
from khimeras_shared.guidance import build_turn_guidance

# Los facts de un usuario con historia: alimentan `medical_history`.
FACTS_CON_INTENTO = [{"fact": "tuvo un intento de suicidio el año pasado"}]


# ---------------------------------------------------------------------------
# Positivo — las cinco filas de la tabla del issue
# ---------------------------------------------------------------------------

# (mensaje, facts, banda esperada, gravedad esperada)
LAS_CINCO_FILAS = [
    ("tengo un plan suicida", FACTS_CON_INTENTO, "CRITICAL", 10.0),
    ("ando con ideación suicida pasiva", None, "HIGH", 7.0),
    ("estoy con desesperanza", None, "HIGH", 7.0),
    ("estoy en duelo", None, "MEDIUM", 5.0),
    ("hoy comí rico y salí a caminar", None, "LOW", 0.0),
]


@pytest.mark.parametrize("mensaje,facts,banda,gravedad", LAS_CINCO_FILAS)
def test_las_cinco_filas_de_la_tabla(mensaje, facts, banda, gravedad):
    """La tabla que Bernard puso en el issue, verificada contra el env real."""
    r = crisis_band(mensaje, facts)
    assert r.level.value == banda, f"{mensaje!r} dio {r.level.value}, no {banda}"
    assert r.final_gravity == gravedad


def test_el_plan_suicida_con_antecedente_dispara_el_override():
    """La fila 1 no es sólo gravedad 10: es override, y eso hay que verlo."""
    r = crisis_band("tengo un plan suicida", FACTS_CON_INTENTO)
    assert r.critical_override is True


def test_un_veredicto_sin_razon_no_es_auditable():
    """Criterio de aceptación del issue: `reasons` nunca vacío fuera de LOW."""
    for mensaje, facts, banda, _ in LAS_CINCO_FILAS:
        r = crisis_band(mensaje, facts)
        if r.level.value != "LOW":
            assert r.reasons, f"{mensaje!r} dio {banda} sin una sola razón"


# ---------------------------------------------------------------------------
# Guardián — el reloj de urgencias se queda AFUERA
# ---------------------------------------------------------------------------
#
# `time_to_action` dice "immediate (<5 min)". Eso es de una sala de urgencias,
# no de un chat: esta persona no puede correr, no puede llamar a nadie y no
# puede ofrecer cuerpo. Si ese texto se le filtra a alguien, el port salió mal.

TIEMPOS_DE_URGENCIAS = tuple(b.time_to_action for b in URGENCY_BANDS)


@pytest.mark.parametrize("mensaje,facts,_banda,_gravedad", LAS_CINCO_FILAS)
def test_el_reloj_de_urgencias_no_llega_al_guidance(mensaje, facts, _banda, _gravedad):
    guidance = build_turn_guidance(
        current_message=mensaje,
        recent_messages=[],
        user_facts=facts,
        persona_id="insult",
    )
    if guidance is None:
        pytest.skip("sin guidance para este turno; el guardián no aplica")
    for reloj in TIEMPOS_DE_URGENCIAS:
        assert reloj not in guidance, f"se filtró el reloj de urgencias: {reloj!r}"


def test_modo_observacion_la_banda_no_entra_al_texto():
    """La banda se registra, no se dice. Ningún nombre de banda en el guidance."""
    guidance = build_turn_guidance(
        current_message="tengo un plan suicida",
        recent_messages=[],
        user_facts=FACTS_CON_INTENTO,
        persona_id="insult",
    )
    assert guidance
    for banda in ("CRITICAL", "critical_override", "final_gravity"):
        assert banda not in guidance


# ---------------------------------------------------------------------------
# El acento — resuelto de este lado, reusando el `_fold` del #52
# ---------------------------------------------------------------------------

PARES_CON_Y_SIN_ACENTO = [
    ("ando con ideación suicida", "ando con ideacion suicida", "HIGH"),
    ("tengo un ataque de pánico", "tengo un ataque de panico", "MEDIUM"),
    ("quiero hacerme daño", "quiero hacerme dano", "CRITICAL"),
]


@pytest.mark.parametrize("con,sin,banda", PARES_CON_Y_SIN_ACENTO)
def test_escribir_sin_acentos_no_baja_la_banda(con, sin, banda):
    """En Discord nadie escribe con acentos.

    El `UrgencyClassifier` de fi-core empareja por substring sobre texto en
    minúsculas y **no** normaliza acentos: 16 frases de PSYCHIATRY bajan de
    banda sin ellos, y 5 caen de CRITICAL a LOW. Este módulo lo compensa
    buscando la forma plegada y entregándole al clasificador la CANÓNICA.
    Si alguien quita ese paso, este test truena.

    Se afirma la banda ESPERADA, no sólo que las dos coincidan: comparar la
    forma con acento contra la forma sin acento pasa de a gratis cuando las dos
    se rompen igual. Se descubrió mutando el módulo el 2026-09-01.
    """
    assert crisis_band(con).level.value == banda
    assert crisis_band(sin).level.value == banda
    assert crisis_band(con).final_gravity == crisis_band(sin).final_gravity


def test_la_forma_canonica_es_la_que_se_entrega():
    """Se detecta sin acento pero se pasa con acento — es lo que lo arregla."""
    assert symptoms_in_message("ando con ideacion suicida") == ["ideación suicida"]


# ---------------------------------------------------------------------------
# Resistencia — los defectos de fi-core, DECLARADOS, no escondidos
# ---------------------------------------------------------------------------


def test_el_defecto_de_sin_medido_tras_fi_core_0_27_0():
    """Por qué este PR SIGUE siendo observación y no producción.

    `_strip_negations` de fi-core trataba "sin" como cue de negación y se comía
    la frase: "mejor sin mí" quedaba en "mejor  " antes de que la lista
    alcanzara a verla. La frase **estaba** en `PSYCHIATRY.high_symptoms` y aun
    así puntuaba 3, el default para lo desconocido.

    fi-core 0.27.0 lo arregló **a medias**, y este test lo mide:

      frase                            v4.38.0   con 0.27.0
      "el equipo va a estar mejor      LOW (3)   HIGH (7)   ✅ arreglado
       sin mí"
      "me siento sin esperanza"        LOW (3)   LOW (0)    ❌ sigue hundida

    La primera es de las cuatro que Álex adoptó una por una el 2026-08-27, y ya
    sale bien. La segunda sigue cayendo a LOW, y por eso la banda se queda en
    observación (decidido el 2026-09-03).

    Este test NO pide que lo que falta se arregle aquí: es de fi-core, y está
    reportado. Pide dos cosas — que lo ya arreglado **no se vuelva a romper**, y
    que si alguien arregla "sin esperanza" río arriba, **este test truene** y
    obligue a revisar si ya se puede encender la banda.
    """
    assert crisis_band("el equipo va a estar mejor sin mí").level.value == "HIGH", (
        "'mejor sin mí' volvió a hundirse — fi-core 0.27.0 la había arreglado. "
        "Es una regresión río arriba, no un cambio de este módulo."
    )
    assert crisis_band("me siento sin esperanza").level.value == "LOW", (
        "'me siento sin esperanza' ya NO cae a LOW — el defecto de 'sin' pudo "
        "haberse arreglado del todo en fi-core. Revisar si ya se puede encender "
        "la banda."
    )


def test_mejor_sin_mi_sigue_disparando_la_ruta_de_hoy():
    """El seguro: mientras la banda no se consuma, no se pierde nada.

    Es exactamente lo que el modo observación protege — el booleano de hoy sigue
    mandando y sigue atrapando esta frase.
    """
    assert is_acute_crisis("el equipo va a estar mejor sin mí") is True


def test_la_banda_ya_resuelve_un_falso_positivo_del_52():
    """Y aquí se ve para qué sirve todo esto.

    "no me quiero suicidar, es broma" es uno de los falsos positivos que Álex
    aceptó a propósito en el #52 — hoy recibe el modo completo. La banda lo pone
    en LOW sola, porque el borrador de negaciones **sí** hace bien su trabajo
    con "no". Este es el arreglo que el #53 existe para traer.
    """
    assert is_acute_crisis("no me quiero suicidar, es broma") is True
    assert crisis_band("no me quiero suicidar, es broma").level.value == "LOW"


# ---------------------------------------------------------------------------
# La historia del usuario alimenta `medical_history`
# ---------------------------------------------------------------------------


def test_la_historia_se_traduce_a_condiciones_de_riesgo():
    assert history_conditions(FACTS_CON_INTENTO) == ["intento de suicidio previo"]


def test_sin_facts_no_hay_condiciones():
    assert history_conditions(None) == []
    assert history_conditions([]) == []


def test_un_mensaje_vacio_no_truena_ni_inventa_banda():
    r = crisis_band("", None)
    assert r.level.value == "LOW"
    assert r.final_gravity == 0.0
    assert symptoms_in_message("") == []
