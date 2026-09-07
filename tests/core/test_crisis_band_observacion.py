"""La crisis deja de ser un booleano y pasa a ser una banda (issue #53, PR 1 de 2).

Este PR corre en **MODO OBSERVACIÓN**, decisión de Álex del 2026-09-01 y
ratificada el 2026-09-03 ya con fi-core 0.27.0: la banda se calcula y se
registra, y **no cambia lo que una persona lee**. La razón estaba medida en
`test_el_defecto_de_sin_medido_tras_fi_core_0_27_0` — 0.27.0 arregló "mejor sin
mí", pero "sin esperanza" seguía en LOW porque esa frase NO ESTABA en el
vocabulario de PSYCHIATRY (issue #64). **fi-core 0.28.0 (2026-09-07) la metió**,
y ese test tronó como estaba diseñado para tronar: hoy las dos frases dan HIGH
(`test_los_dos_defectos_de_sin_ya_no_existen_con_fi_core_0_28_0`). El mismo día
0.29.0 trajo las H1/H2 de Álex (fi #461): exclusiones y los grupos de exposición,
fijados abajo desde el consumidor. Ya no hay detección que se pierda por
encender la banda; lo que falta es la semana de log y la decisión de Álex — el
segundo PR del #53 sigue siendo suyo.

Regla del mutador, la misma del #52: positivo (la tabla del issue da lo que
promete) + resistencia (los defectos de fi-core declarados uno por uno, no
escondidos) + guardián (el reloj de urgencias NUNCA le llega a una persona).
"""

from __future__ import annotations

import pytest
from fi_core.cognitive import PSYCHIATRY, URGENCY_BANDS

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


def test_los_dos_defectos_de_sin_ya_no_existen_con_fi_core_0_28_0():
    """La historia de por qué este PR fue observación, y por qué ya no por esto.

    Las dos frases caían a LOW por razones DISTINTAS, y el #53 las metió en el
    mismo saco. Medido versión por versión (issue #64):

      frase                            v4.38.0   0.27.0    0.28.0   por qué
      "el equipo va a estar mejor      LOW (3)   HIGH (7)  HIGH (7) el bug de "sin"
       sin mí"                                                       (0.27.0)
      "me siento sin esperanza"        LOW (3)   LOW (0)   HIGH (7) la frase NO
                                                                     ESTABA (0.28.0)

    **La segunda nunca fue el bug de negación.** `PSYCHIATRY` traía
    `"desesperanza"` en una sola palabra y `"siento desesperanza"` sí subía a
    HIGH; `"sin esperanza"` —la forma coloquial, la que la gente escribe en
    Discord— simplemente no existía en la lista. fi-core 0.28.0 la agregó (con
    "no tengo esperanza" y las formas en primera persona) y además hizo la
    negación LOCAL: "sin"/"no"/"nunca" niegan a una palabra de distancia y
    nunca cruzan una coma, así que "sin" ya no puede comerse una frase que
    está tres palabras después.

    La versión anterior de este test afirmaba el LOW a propósito, para tronar
    el día que el vocabulario cambiara río arriba y obligar a revisar si ya se
    puede encender la banda. Tronó el 2026-09-07 al subir el pin. Ese día se
    revisó: **ya no hay detección que se pierda** por graduar — pero encender
    la banda sigue siendo el segundo PR del #53 y sigue siendo decisión de Álex
    con la semana de log enfrente, no un efecto colateral del bump.

    Lo que este test fija ahora: que ninguna de las dos **vuelva** a hundirse.
    """
    assert crisis_band("el equipo va a estar mejor sin mí").level.value == "HIGH", (
        "'mejor sin mí' volvió a hundirse — fi-core 0.27.0 la había arreglado. "
        "Es una regresión río arriba, no un cambio de este módulo."
    )
    assert crisis_band("me siento sin esperanza").level.value == "HIGH", (
        "'me siento sin esperanza' volvió a LOW — fi-core 0.28.0 la había metido "
        "al vocabulario (#64). Es una regresión río arriba, no un cambio de este módulo."
    )


def test_la_negacion_local_no_cruza_una_coma():
    """El diseño de 0.28.0, fijado desde el consumidor.

    "no" niega lo que tiene a una palabra; una coma corta el alcance. Si río
    arriba vuelven a la negación por oración entera, la primera frase se hunde
    y este test lo dice antes que un log de #general.
    """
    assert crisis_band("no me quiero morir, pero ya no puedo más").level.value == "LOW"
    assert is_acute_crisis("no me quiero morir, pero ya no puedo más") is True
    assert symptoms_in_message("no tengo esperanza, tengo un plan suicida") == ["no tengo esperanza", "plan suicida"]


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
    en LOW sola, porque `match()` lo devuelve en `denied`, no en `symptoms`.

    Y el booleano sigue disparando aunque desde v4.38.9 también pasa por
    `match()`: lo que lo dispara aquí es `acute_signals` (los 5 regex bilingües
    que Álex decidió conservar, "que se queden las dos"), que desde 0.29.0 sí
    respeta la negación local — "no me quiero morir" ya no cruza — pero en ESTA
    frase el regex de ideación explícita pega en "suicidar", a dos palabras del
    "no", fuera de la ventana. Es la única grieta medida entre las dos capas y
    vive en fi-core, no aquí; se fija para que el día que se cierre, se note.
    Este es el arreglo que el #53 existe para traer.
    """
    assert PSYCHIATRY.match("no me quiero suicidar, es broma").denied == ("me quiero suicidar",)
    assert PSYCHIATRY.acute_signals.score(["no me quiero suicidar, es broma"]).matched == ("explicit_ideation",)
    assert is_acute_crisis("no me quiero suicidar, es broma") is True
    assert crisis_band("no me quiero suicidar, es broma").level.value == "LOW"


# ---------------------------------------------------------------------------
# Las H1/H2 de Álex, fijadas desde el consumidor (fi-core 0.29.0, fi #461)
# ---------------------------------------------------------------------------


def test_la_exposicion_al_suicidio_de_un_tercero_es_historia_no_crisis():
    """ "mi hermana intentó suicidarse" no es crisis del hablante.

    Hasta v4.38.8 disparaba el booleano por subcadena. 0.29.0 lo aparta en
    `excluded` (grupo `exposicion_intento`) y ese mismo grupo cuenta en el
    eje CRÓNICO: como fact, entra a `medical_history` por `_GROUP_TO_CONDITION`
    y suma +0.5 a la banda, no la cruza sola. Y "mi paciente intentó
    suicidarse" sigue CRITICAL a propósito (decisión de Álex, pinneada en
    fi-core `tests/test_psychiatry_h1_h2.py`).
    """
    frase = "mi hermana intentó suicidarse"
    assert PSYCHIATRY.match(frase).excluded == ("exposicion_intento",)
    assert is_acute_crisis(frase) is False
    assert crisis_band(frase).level.value == "LOW"
    assert crisis_band("mi paciente intentó suicidarse").level.value == "CRITICAL"

    facts = [{"fact": "su hermana intentó suicidarse"}, {"fact": "su tío se suicidó el año pasado"}]
    assert history_conditions(facts) == [
        "exposición a intento de suicidio",
        "exposición a suicidio consumado",
    ]


def test_la_historia_sola_dispara_el_override_critical_y_eso_es_de_fi_core():
    """El defecto que hoy más pesa contra encender la banda — DECLARADO.

    `UrgencyClassifier.critical_pattern()` (fi-core 0.29.0, `urgency.py`)
    busca los `critical_patterns` en `symptoms + medical_history` PEGADOS. Como
    "intento de suicidio" es un patrón crítico, cualquier condición de historia
    que lo contenga — "intento de suicidio previo", y desde 0.29.0 también
    "exposición a intento de suicidio" — dispara el override CRITICAL en TODOS
    los turnos de esa persona, con el mensaje que sea, incluso vacío. En una
    sala de urgencias eso es triage razonable; en un chat es una banda que no
    distingue "hoy comí rico" de "tengo un plan suicida" para quien tiene
    antecedente, que es exactamente la gente para la que la banda existe.

    Este test NO pide arreglarlo aquí (es de fi-core, reportado el 2026-09-07 a
    la sesión que lo mantiene). Pide que el día que río arriba la historia deje
    de contar como patrón crítico, esto truene y obligue a revisar si la banda
    ya puede salir de observación. Misma regla que el sentinel de "sin": el
    defecto se fija, no se esconde.
    """
    con_intento = crisis_band("hoy comí rico y salí a caminar", FACTS_CON_INTENTO)
    assert con_intento.level.value == "CRITICAL"
    assert con_intento.critical_override is True
    assert "intento de suicidio" in con_intento.reasons[0]

    exposicion = [{"fact": "su hermana intentó suicidarse"}]
    assert crisis_band("hoy comí rico y salí a caminar", exposicion).level.value == "CRITICAL"
    assert crisis_band("", exposicion).level.value == "CRITICAL"


@pytest.mark.parametrize(
    ("frase", "excluido"),
    [
        ("me morí de la risa", ()),
        ("vi un documental sobre suicidio", ("tema_no_propio",)),
        ("no puedo más con este proyecto", ("desahogo_laboral",)),
    ],
)
def test_las_exclusiones_de_alex_no_suben_la_banda(frase, excluido):
    """Modismo, tema ajeno y desahogo laboral: LOW, y el motivo queda dicho."""
    assert PSYCHIATRY.match(frase).excluded == excluido
    assert crisis_band(frase).level.value == "LOW"
    assert is_acute_crisis(frase) is False


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
