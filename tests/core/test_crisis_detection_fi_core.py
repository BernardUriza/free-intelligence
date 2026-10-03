"""La detección de crisis deja de ser 5 regex locales y pasa a fi-core (issue #52).

Antes de este cambio, `is_acute_crisis` eran cinco expresiones regulares escritas
a mano, y `PSYCHIATRY` —una lista clínica en español que este repo ya tenía
instalada— no se usaba para nada. Se perdían **38 de las 51** frases de
`critical_symptoms`: "plan suicida", "quitarme la vida", "cortarse las venas",
"envenenarse", "no quiero seguir viviendo".

Regla del mutador: positivo (cada frase adoptada dispara la ruta de crisis) +
resistencia (el corpus de falsos positivos que escribió Álex, con chiste y
modismo, y el trade-off que se aceptó a propósito y NO se esconde).
"""

from __future__ import annotations

import pytest
from fi_core.cognitive import PSYCHIATRY

from persona_core.behavior.vulnerability import (
    VULNERABLE_THRESHOLD,
    compute_vulnerability_score,
    is_acute_crisis,
    matched_signal_groups,
)

# Las 30 frases que YA disparaban con los 5 regex locales, antes de borrarlos.
# Si alguna deja de disparar, el cambio costó detección en vez de sumarla.
CORPUS_VIEJO = (
    "suicidarme",
    "matarme",
    "me quiero morir",
    "autolesionarme",
    "kill myself",
    "i want to die",
    "self-harm",
    "no puedo más",
    "ya no aguanto",
    "no puedo seguir",
    "i can't go on",
    "me rindo",
    "estoy en crisis",
    "i'm in crisis",
    "ataque de pánico",
    "panic attack",
    "estoy muy mal",
    "i'm not safe",
    "ayuda en serio",
    "help me for real",
    "no estoy bien para nada",
    "estoy mal de verdad",
    "no tengo a nadie",
    "me siento muy solo de verdad",
    "i feel so alone right now",
)

# Las 4 señales tempranas que Álex adoptó una por una el 2026-08-27.
ADOPTADAS_HIGH = (
    "mejor sin mí",
    "para qué seguir",
    "no le veo sentido",
    "ya no quiero estar",
)

# El corpus de falsos positivos lo escribió Álex el 2026-08-26: frases que
# alguien diría de verdad en #general. Estas cuatro son chiste y modismo puro.
FALSOS_POSITIVOS_LIMPIOS = (
    "morí de risa",
    "muero de la risa",
    "me mató de risa",
    "me he estado matando en la chamba",
)

# Y estas cinco son el precio, medido y aceptado a propósito el 2026-08-31.
# Cada una trae adentro una frase adoptada. NO se esconden: si algún día el
# #53 las gradúa con bandas, este test es el que se pone rojo y avisa.
FALSOS_POSITIVOS_ACEPTADOS = (
    ("para qué seguir con lo mismo", "para qué seguir"),
    ("ya no quiero estar en una relación", "ya no quiero estar"),
    ("no le veo sentido a seguir en ese trabajo", "no le veo sentido"),
    ("quiero morir de vergüenza", "quiero morir"),
    ("no quiero seguir viviendo una vida recordando a mi ex por siempre", "no quiero seguir viviendo"),
)

# Eran seis. Ésta salió sola el 2026-09-07 (v4.38.9) cuando el booleano dejó
# de buscar subcadenas plegadas y pasó a `PSYCHIATRY.match()`: fi-core 0.28.0
# lee el "no" a una palabra de "hacerme daño" y la devuelve en `denied`. Fue
# la ÚNICA frase de los corpus de Álex que cambió con la migración — medido
# antes de borrar la copia local del plegado. (Fuera de sus corpus cambiaron
# tres más, todas negadas o de exposición: ver NEGADAS_QUE_YA_NO_DISPARAN.)
FALSOS_POSITIVOS_RESUELTOS_POR_MATCH = (("ya no quiero hacerme daño pensando en mi ex", "hacerme daño"),)

# Lo que el booleano dejó de disparar con fi-core 0.29.0 sin que nadie lo
# graduara: la negación local llegó a `acute_signals` (fi #461, H1/H2). Cada
# fila trae la señal que SÍ dispara sola, para que el test no pase de a gratis.
NEGADAS_QUE_YA_NO_DISPARAN = (
    ("no me quiero morir", "me quiero morir"),
    ("no me quiero morir, solo estoy muy cansado", "me quiero morir"),
    # Ésta la alcanzó la ventana hasta 0.29.1 (cue → clítico → verbo).
    ("no me quiero suicidar, es broma", "me quiero suicidar"),
)


# --- POSITIVO: lo que el issue existe para recuperar --------------------------


@pytest.mark.parametrize("frase", sorted(PSYCHIATRY.critical_symptoms))
def test_every_critical_symptom_routes_to_crisis(frase: str):
    """Las 51 de `critical_symptoms`. Antes de este cambio se perdían 38."""
    assert is_acute_crisis(frase), f"'{frase}' no dispara la ruta de crisis"


@pytest.mark.parametrize("frase", ADOPTADAS_HIGH)
def test_every_adopted_early_signal_routes_to_crisis(frase: str):
    """Las 4 que Álex decidió el 27, viendo dos mensajes reales por frase.

    Son las señales que alguien dice ANTES de decir las de arriba.
    """
    assert is_acute_crisis(frase), f"'{frase}' no dispara, y Álex decidió que sí"


@pytest.mark.parametrize("frase", CORPUS_VIEJO)
def test_the_local_regexes_lost_nothing_when_they_were_deleted(frase: str):
    """Unión, no reemplazo — la decisión de Álex el 2026-08-27: "que se queden las dos".

    Los 5 regex locales se borraron porque fi-core 0.26.0 los trae verbatim,
    bilingües. Si este test se pone rojo, se borraron de más.
    """
    assert is_acute_crisis(frase), f"'{frase}' disparaba antes del cambio y ya no"


def test_ya_no_puedo_mas_still_fires():
    """La frase con la que Valentis contestó por primera vez en Discord, el 25.

    No está en `PSYCHIATRY.critical_symptoms`. Es el dato que más pesó cuando
    Álex decidió que los regex no se reemplazaban a lo tonto.
    """
    assert is_acute_crisis("ya no puedo más")


# --- Los acentos, en las DOS direcciones --------------------------------------


@pytest.mark.parametrize(
    ("con_acento", "sin_acento"),
    [
        ("hacerme daño", "hacerme dano"),
        ("autolesión activa", "autolesion activa"),
        ("ideación homicida", "ideacion homicida"),
        ("para qué seguir", "para que seguir"),
    ],
)
def test_accents_fire_both_ways(con_acento: str, sin_acento: str):
    """En Discord la mitad de la gente escribe sin acentos.

    La lista de fi-core viene acentuada; si sólo se comparara contra eso, media
    lista no dispararía para quien teclea de corrido.
    """
    assert is_acute_crisis(con_acento)
    assert is_acute_crisis(sin_acento)


@pytest.mark.parametrize("frase", ["desesperanza", "ideación de muerte", "disociación"])
def test_the_high_symptoms_alex_did_not_adopt_stay_out(frase: str):
    """`high_symptoms` tiene 17 frases y Álex adoptó 4, no las 17.

    Las otras 13 —desesperanza, ideación de muerte, disociación— siguen sin
    disparar a propósito. Si algún día entran, que sea una decisión suya y no
    un efecto colateral de tocar el import.
    """
    assert frase not in ADOPTADAS_HIGH
    assert not is_acute_crisis(frase)


def test_the_phrase_fires_inside_a_longer_sentence():
    """Nadie escribe "plan suicida" y ya. Lo dice dentro de un párrafo."""
    assert is_acute_crisis("llevo días con un plan suicida y no se lo he dicho a nadie")


# --- CONTROL NEGATIVO: sin esto, el test de arriba no prueba nada -------------


@pytest.mark.parametrize("frase", FALSOS_POSITIVOS_LIMPIOS)
def test_alex_jokes_do_not_route_to_crisis(frase: str):
    """El chiste y el modismo NO son crisis.

    Este repo ya pagó esa factura: forzar presencia de crisis sobre alguien que
    estaba bromeando produce respuestas planas para quien sólo quería platicar
    de su día. Es la regresión que aplanó a Álex en el turno del DIF.
    """
    assert not is_acute_crisis(frase), f"'{frase}' es un chiste y disparó crisis"


@pytest.mark.parametrize(("frase", "señal"), FALSOS_POSITIVOS_ACEPTADOS)
def test_the_accepted_false_positives_are_declared_not_hidden(frase: str, señal: str):
    """El precio del cambio, escrito con nombre y apellido.

    Estas seis frases las escribió Álex como ejemplos de lo que NO debería
    disparar, y disparan. La decisión fue suya el 2026-08-31, con los números
    enfrente: se atiende de más a quien no lo necesitaba, en vez de no atender
    a quien sí. El arreglo de fondo —graduar por banda en vez de sí/no— es el
    issue #53.

    Este test NO celebra el falso positivo: lo fija. Cuando el #53 gradúe,
    se pone rojo y obliga a revisar cada una.
    """
    assert is_acute_crisis(frase)
    assert is_acute_crisis(señal), f"la señal '{señal}' es la que lo dispara"


@pytest.mark.parametrize(("frase", "señal"), FALSOS_POSITIVOS_RESUELTOS_POR_MATCH)
def test_a_negated_signal_no_longer_routes_to_crisis(frase: str, señal: str):
    """El primer falso positivo aceptado que se resuelve sin graduar nada.

    La señal sigue disparando sola; negada a una palabra de distancia, ya no.
    Es exactamente lo que `denied` existe para decir: la persona lo está
    negando. Si `match()` deja de ver la negación, esto vuelve a disparar y el
    test lo dice.
    """
    assert is_acute_crisis(señal), f"la señal '{señal}' dejó de disparar sola"
    assert PSYCHIATRY.match(frase).denied == (señal,)
    assert not is_acute_crisis(frase), f"'{frase}' está negada y volvió a disparar"


@pytest.mark.parametrize(("frase", "señal"), NEGADAS_QUE_YA_NO_DISPARAN)
def test_a_negated_regex_signal_no_longer_routes_to_crisis(frase: str, señal: str):
    """Los 5 regex también leen el "no" desde fi-core 0.29.0.

    Antes "no me quiero morir" disparaba el modo completo por el regex de
    ideación explícita, ciego a la negación. Ahora queda en `denied` del eje
    agudo. Si río arriba el regex vuelve a ignorar el "no", esto avisa.
    """
    assert is_acute_crisis(señal), f"la señal '{señal}' dejó de disparar sola"
    assert "explicit_ideation" in PSYCHIATRY.acute_signals.score([frase]).denied
    assert not is_acute_crisis(frase), f"'{frase}' está negada y volvió a disparar"


# --- El eje crónico: mismos pesos, mismo umbral -------------------------------


def test_the_threshold_still_comes_out_at_four():
    """El valor se borró de aquí, no se cambió. Vive en fi-core, verbatim."""
    assert VULNERABLE_THRESHOLD == 4
    assert PSYCHIATRY.chronic_signals.threshold == 4


def test_a_real_cluster_still_crosses():
    """Diagnóstico + medicación cruza, como antes de mover el corpus."""
    facts = [{"fact": "tengo cptsd"}, {"fact": "tomo sertralina"}]
    assert compute_vulnerability_score(facts) == 6
    assert set(matched_signal_groups(facts)) == {"named_diagnosis", "psychiatric_medication"}


def test_an_isolated_metaphor_still_does_not_cross():
    """ "Estoy traumado con el código legacy" no es vulnerabilidad clínica.

    Era el riesgo de migrar antes de fi-core 0.26.0. Ya no pasa.
    """
    assert compute_vulnerability_score([{"fact": "estoy traumado con el código legacy"}]) == 0


def test_redundant_facts_about_one_drug_do_not_inflate_the_score():
    """El extractor emite 2-5 facts del mismo evento. Cuentan como uno.

    La vulnerabilidad pide un clúster, no menciones repetidas del mismo fármaco.
    """
    facts = [
        {"fact": "toma sertralina"},
        {"fact": "tomó su primera pastilla de sertralina"},
        {"fact": "sertralina 50mg"},
    ]
    assert compute_vulnerability_score(facts) == 3
    assert compute_vulnerability_score(facts) < VULNERABLE_THRESHOLD


@pytest.mark.parametrize(
    ("nombre", "frase"),
    [
        ("abuse", "viví abuso en mi infancia"),
        ("recent_grief", "se murió mi papá hace dos meses"),
    ],
)
def test_the_four_orphan_categories_now_score_but_do_not_cross_alone(nombre: str, frase: str):
    """Abuso, aislamiento, duelo y sustancias: el repo no las detectaba.

    Entran con este cambio porque vienen dentro de `chronic_signals`. Álex lo
    decidió el 2026-08-31 con la medición enfrente: **suman pero no cruzan
    solas** — el umbral sigue en 4 y cada una pesa 2. Sus pesos son PROPUESTOS
    y se validan en el #55.
    """
    facts = [{"fact": frase}]
    assert nombre in matched_signal_groups(facts)
    assert compute_vulnerability_score(facts) < VULNERABLE_THRESHOLD


# --- Que no se copiaron las listas -------------------------------------------


def test_the_lists_are_imported_not_copied():
    """El corazón del issue: fi-core es la fuente.

    Si alguien pega las frases de vuelta al repo, fi-core deja de ser la fuente
    y la mejora de Bernard ya no se hereda gratis. El grep de cero referencias
    a `_ACUTE_CRISIS_PATTERNS` y `_SIGNAL_GROUPS` va en el PR; esto cubre el
    otro lado, que el módulo de verdad lee de fi-core en tiempo de ejecución.
    """
    from persona_core.behavior import vulnerability

    fuente = vulnerability.__file__
    with open(fuente, encoding="utf-8") as fh:
        codigo = fh.read()

    # Identidad de objeto, no cadena de texto (endurecido el 2026-09-01): buscar
    # la línea del import se rompía con sólo reformatearlo, y una copia local
    # con el mismo nombre lo habría pasado. Esto exige que sea EL objeto de
    # fi-core, no uno igualito.
    import fi_core.cognitive

    assert vulnerability.PSYCHIATRY is fi_core.cognitive.PSYCHIATRY
    assert "_ACUTE_CRISIS_PATTERNS" not in codigo
    assert "_SIGNAL_GROUPS" not in codigo
    # Una frase clínica cualquiera de la lista NO debe estar escrita en el repo.
    assert "cortarse las venas" not in codigo
