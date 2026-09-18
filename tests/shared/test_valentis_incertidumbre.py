"""El guidance de Valentis cuando alguien le trae una interpretación (issue #80).

El guidance del #42 sólo se activa cuando el turno es grave. Esto es otra cosa: la
hermana que no contesta o el jefe que grita no son crisis, y ahí es justo donde una
validación repetida puede endurecer una interpretación hasta que se siente hecho.
Por eso vive en `preset_intentionality_directive`, que el motor carga en TODOS los
turnos, y no en un preset de modo. El ADN del #41 no se toca.

EL CRITERIO es de Álex, textual, del 2026-09-18: "no reforzaría una creencia o
interpretación sin tener más evidencia de la dinámica". Los ocho casos salieron de
ejemplos concretos, como en el #42: Claude propuso respuestas y Álex tachó y eligió.
En todos quedaron fuera las dos puntas —la que confirma y la que contradice—.
Los dos últimos son la parte 2 del issue, las señales de que una idea se está
volviendo rígida, vigiladas SÓLO dentro de la conversación (decisión de Álex: nada
nuevo se guarda por persona entre días).

Lo que se protege, y por qué cada cosa:

Positivo:
  1. el cableado: `build_preset_prompt` devuelve ESTE texto para Valentis en un
     modo que NO es grave, con control negativo al lado.

Resistencia — cada una es una decisión clínica que se puede perder reescribiendo:
  1. el criterio de Álex, palabra por palabra;
  2. las dos puntas: nunca confirma y nunca discute. Sin la segunda, "incertidumbre"
     se vuelve una Valentis que contradice, y el issue pide lo contrario;
  3. los ocho casos siguen distinguidos. Colapsarlos es volver a "no le des la razón
     a todo", que es exactamente el hueco;
  4. con evidencia no se siembran dudas, y la pregunta no suena a culpa. Álex
     ajustó "¿qué pasó antes de que te gritara?" porque se leía como "¿qué hiciste
     tú?";
  5. en la dependencia, el mérito es de quien escribe, no de Valentis;
  6. los moldes no se recitan: por deducción, no por lista;
  7. no se nombra un sentimiento que quien escribe no ha nombrado;
  8. cuando rechaza la otra lectura, Valentis no insiste, no cede y no le señala
     el patrón (el ADN ya dice que los patrones se abren como pregunta).
"""

from __future__ import annotations

from pathlib import Path

from khimeras_shared.behavior.contracts.presets import PresetMode, PresetSelection
from khimeras_shared.behavior.presets.guidance import build_preset_prompt

GUIDANCE = (
    Path(__file__).resolve().parents[2]
    / "shared"
    / "personas"
    / "guidance"
    / "valentis"
    / "presets"
    / "preset_intentionality_directive.md"
)

CRITERIO_DE_ALEX = "No refuerzas una creencia o interpretación sin tener más evidencia de la dinámica."


def _texto() -> str:
    return GUIDANCE.read_text(encoding="utf-8")


def _modo_no_grave() -> PresetSelection:
    modo = next(m for m in PresetMode if m is not PresetMode.RESPECTFUL_SERIOUS)
    return PresetSelection(mode=modo, reason="test")


def test_the_wire_reaches_valentis_on_an_ordinary_turn():
    """POSITIVO: llega en un turno que NO es grave, con control negativo al lado."""
    entregado = build_preset_prompt(_modo_no_grave(), "valentis")
    assert CRITERIO_DE_ALEX in entregado, "el motor no encontró el archivo: revisa el NOMBRE"
    assert CRITERIO_DE_ALEX not in build_preset_prompt(_modo_no_grave(), "__persona_that_never_existed__")


def test_alex_criterion_survives_word_for_word():
    """RESISTENCIA: el criterio es de Álex y no se parafrasea."""
    assert CRITERIO_DE_ALEX in _texto()


def test_both_ends_are_ruled_out():
    """RESISTENCIA: ni confirmar ni contradecir."""
    assert "Nunca confirmas y nunca discutes." in _texto()


def test_no_feeling_is_named_before_whoever_writes_names_it():
    """RESISTENCIA: no se le pone a nadie un sentimiento que no ha dicho.

    Criterio de Álex del 2026-09-18, al revisar los moldes: "menciona la palabra
    duele cuando quien escribe no ha habló de sentimientos". Por eso los moldes
    de los casos 1 y 5 perdieron su "duele" y su "te cansó". El test guarda la
    regla y que no regresen.
    """
    texto = _texto()
    assert "no nombras un sentimiento que quien te escribe no ha nombrado" in texto
    assert "Duele no tener respuesta" not in texto
    assert "Se nota que te cansó" not in texto


def test_the_eight_cases_survive():
    """RESISTENCIA: los ocho casos siguen distinguidos."""
    texto = _texto()
    for caso in (
        "La idea es sobre otra persona",
        "La idea se repite",
        "La idea es sobre sí misme",
        "Sí hay evidencia",
        "Te piden la razón directo",
        "Te vuelves su forma de calmarse",
        "Rechaza la otra lectura",
        "La idea ya viene como hecho",
    ):
        assert caso in texto, f"se perdió el caso: {caso}"


def test_evidence_is_not_doubted_and_the_question_carries_no_blame():
    """RESISTENCIA: con evidencia no se siembran dudas, y la pregunta no culpa."""
    texto = _texto()
    assert "No siembras dudas que no existen" in texto
    assert "¿Qué sucedió? Si quieres contarme más de eso, aquí estoy." in texto
    assert "qué pasó antes de que te gritara" not in texto.lower()


def test_calming_down_is_credited_to_whoever_writes():
    """RESISTENCIA: en la dependencia, el mérito es de quien escribe."""
    assert "quien se calma eres tú" in _texto()


def test_the_molds_are_not_recited():
    """RESISTENCIA: por deducción, no por lista."""
    assert "Los moldes enseñan el criterio. No se recitan." in _texto()


def test_a_rejected_reading_is_neither_pushed_nor_conceded():
    """RESISTENCIA: ante el rechazo, ni insistir ni ceder ni señalar el patrón."""
    texto = _texto()
    assert "No insistes, no cedes y no le señalas el patrón." in texto
    assert "no te voy a insistir" in texto
