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
    crisis_verdict,
    is_acute_crisis,
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
    assert crisis_verdict("ando con ideacion suicida").hits.symptoms == ("ideación suicida",)


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
    assert crisis_verdict("no tengo esperanza, tengo un plan suicida").hits.symptoms == (
        "no tengo esperanza",
        "plan suicida",
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
    en LOW sola, porque `match()` lo devuelve en `denied`, no en `symptoms`.

    Y desde v4.38.10 el booleano tampoco dispara. Con 0.29.0 todavía sí: el
    regex de ideación explícita de `acute_signals` pegaba en "suicidar", a dos
    palabras del "no", fuera de su ventana — la única grieta medida entre las
    dos capas, fijada aquí como defecto declarado y cerrada en fi-core 0.29.1
    (PR #463: la ventana es cue → clítico → verbo, el orden del español). Este
    test tronó con el bump, que era su trabajo. "no sé si me quiero morir"
    sigue positiva a propósito: el "no" no niega el "quiero morir".
    """
    assert PSYCHIATRY.match("no me quiero suicidar, es broma").denied == ("me quiero suicidar",)
    assert PSYCHIATRY.acute_signals.score(["no me quiero suicidar, es broma"]).denied == ("explicit_ideation",)
    assert is_acute_crisis("no me quiero suicidar, es broma") is False
    assert crisis_band("no me quiero suicidar, es broma").level.value == "LOW"
    assert is_acute_crisis("no sé si me quiero morir") is True


# ---------------------------------------------------------------------------
# Las H1/H2 de Álex, fijadas desde el consumidor (fi-core 0.29.0, fi #461)
# ---------------------------------------------------------------------------


def test_la_exposicion_al_suicidio_de_un_tercero_es_historia_no_crisis():
    """ "mi hermana intentó suicidarse" no es crisis del hablante.

    Hasta v4.38.8 disparaba el booleano por subcadena. 0.29.0 lo aparta en
    `excluded` (grupo `exposicion_intento`) y ese mismo grupo cuenta en el
    eje CRÓNICO: como fact, entra a `medical_history` por
    `PSYCHIATRY.chronic_conditions` (fi-core 0.30.0; hasta v4.38.17 era el
    `_GROUP_TO_CONDITION` de este módulo) y suma +0.5 a la banda, no la cruza sola. Y "mi paciente intentó
    suicidarse" sigue CRITICAL a propósito (decisión de Álex, pinneada en
    fi-core `tests/test_psychiatry_h1_h2.py`).
    """
    frase = "mi hermana intentó suicidarse"
    assert PSYCHIATRY.match(frase).excluded == ("exposicion_intento",)
    assert is_acute_crisis(frase) is False
    assert crisis_band(frase).level.value == "LOW"
    assert crisis_band("mi paciente intentó suicidarse").level.value == "CRITICAL"

    facts = [{"fact": "su hermana intentó suicidarse"}, {"fact": "su tío se suicidó el año pasado"}]
    veredicto = crisis_verdict("hoy comí rico", facts)
    assert veredicto.chronic.matched == ("exposicion_consumado", "exposicion_intento")
    assert veredicto.conditions == (
        "exposición a intento de suicidio",
        "exposición a suicidio consumado",
    )


def test_la_historia_sola_ya_no_dispara_el_override_critical():
    """El defecto que más pesaba contra encender la banda — cerrado el mismo día.

    Hasta fi-core 0.29.0, `UrgencyClassifier.critical_pattern()` buscaba los
    `critical_patterns` en `symptoms + medical_history` PEGADOS. Como "intento
    de suicidio" es un patrón crítico, cualquier condición de historia que lo
    contuviera — "intento de suicidio previo", y desde 0.29.0 también
    "exposición a intento de suicidio" — disparaba el override CRITICAL en
    TODOS los turnos de esa persona, con el mensaje que fuera, incluso vacío:
    para quien tiene antecedente, la banda no distinguía "hoy comí rico" de
    "tengo un plan suicida" — exactamente la gente para la que existe. Nadie lo
    vio desde el #53 porque `FACTS_CON_INTENTO` sólo se probaba con "tengo un
    plan suicida". Salió el 2026-09-07 al probar la exposición; se fijó como
    defecto declarado; fi-core 0.29.1 (PR #463) lo arregló: el override sólo
    mira síntomas y la historia se queda con su +0.5. Este test tronó con el
    bump, que era su trabajo; ahora fija el arreglo.
    """
    con_intento = crisis_band("hoy comí rico y salí a caminar", FACTS_CON_INTENTO)
    assert con_intento.level.value == "LOW"
    assert con_intento.critical_override is False
    assert con_intento.final_gravity == 0.5
    assert crisis_band("", FACTS_CON_INTENTO).level.value == "LOW"

    exposicion = [{"fact": "su hermana intentó suicidarse"}]
    assert crisis_band("hoy comí rico y salí a caminar", exposicion).level.value == "LOW"
    assert crisis_band("", exposicion).final_gravity == 0.5

    assert crisis_band("tengo un plan suicida", FACTS_CON_INTENTO).critical_override is True
    assert crisis_band("estoy en duelo", FACTS_CON_INTENTO).final_gravity == 5.5


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
    veredicto = crisis_verdict("hoy comí rico", FACTS_CON_INTENTO)
    assert veredicto.chronic.matched == ("self_harm_history",)
    assert veredicto.conditions == ("intento de suicidio previo",)


def test_sin_facts_no_hay_condiciones():
    assert crisis_verdict("hoy comí rico", None).conditions == ()
    assert crisis_verdict("hoy comí rico", []).conditions == ()


def test_un_mensaje_vacio_no_truena_ni_inventa_banda():
    r = crisis_band("", None)
    assert r.level.value == "LOW"
    assert r.final_gravity == 0.0
    assert crisis_verdict("").hits.symptoms == ()


# ---------------------------------------------------------------------------
# Una lectura, no dos (fi-core 0.30.0, issue #54)
# ---------------------------------------------------------------------------


def test_la_banda_y_su_explicacion_salen_de_la_misma_lectura():
    """Hasta v4.38.17 `matched_acute_groups` era una lectura PARALELA que
    "explicaba el veredicto sin SER el veredicto". Ahora los grupos vienen en
    el mismo `ClinicalVerdict` que la banda, y las razones son tipadas: lo que
    se loguea es `kind`/`key`/`weight`, nunca la frase."""
    v = crisis_verdict("me quiero morir, ya no puedo más", FACTS_CON_INTENTO)
    assert v.level.value == "CRITICAL"
    assert v.score == crisis_band("me quiero morir, ya no puedo más", FACTS_CON_INTENTO)
    assert v.acute.matched == ("at_the_limit", "explicit_ideation")
    assert v.chronic.matched == ("self_harm_history",)
    (razon,) = v.score.reasons
    assert (razon.kind, razon.key, razon.weight) == ("critical_pattern", "critical_patterns", 10)
    assert "quiero morir" not in repr(razon)
    assert razon.render() == "critical pattern 'quiero morir' detected → override CRITICAL"


def test_el_mapa_de_grupo_a_condicion_vive_en_fi_core():
    """El `_GROUP_TO_CONDITION` que vivía aquí es hoy `PSYCHIATRY.chronic_conditions`.
    Se fija desde el consumidor que las ocho entradas siguen siendo las mismas."""
    assert PSYCHIATRY.chronic_conditions == {
        "self_harm_history": "intento de suicidio previo",
        "recent_grief": "duelo reciente",
        "abuse": "abuso",
        "hospitalization": "hospitalización psiquiátrica previa",
        "social_isolation": "aislamiento social",
        "substance_use": "trastorno por uso de sustancias",
        "exposicion_intento": "exposición a intento de suicidio",
        "exposicion_consumado": "exposición a suicidio consumado",
    }
