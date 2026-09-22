"""`named_diagnosis` nombra los diagnósticos más prevalentes — hallazgo 3 de Álex.

Decidido en discord-bot #55 (2026-09-09), re-medido por ella en fi-core 0.32.0
(2026-09-15 y 2026-09-21): seguía en cero. Relevado a fi #490. El grupo cubría
PTSD, TDAH, TOC, bipolar, esquizofrenia, psicosis, disociación — y no cubría
depresión (el más prevalente), los trastornos alimentarios (los de mayor
mortalidad psiquiátrica), borderline en inglés ni ansiedad generalizada. Y
*"trastorno límite"* daba 3 mientras *"borderline personality disorder"* daba 0:
el mismo diagnóstico contando distinto según el idioma.

Sus tres decisiones, que son la spec de este archivo:

1. **Al grupo existente, peso 3, sin partirlo.** Midió dos niveles y sólo un caso
   cambiaba; un diagnóstico solo nunca llega al umbral de 4 de todos modos, y
   decidir cuál "pesa menos" es un juicio que envejece mal escrito en código.
2. **Cuentan solos:** anorexia, bulimia, borderline (en / es). Nadie los dice de
   pasada.
3. **Requieren marcador de diagnóstico** (*me diagnosticaron*, *diagnosticada*,
   *diagnosed with*, *sufro*): depresión / depression y ansiedad generalizada /
   GAD. Sin el marcador, las cuatro coloquiales siguen en cero — el riesgo de
   falso positivo nace el día que se agregan las palabras, así que se decide antes.
"""

from __future__ import annotations

import pytest

from fi_core.cognitive.psychiatry_signals import PSYCH_CHRONIC_SIGNALS as CHRONIC

#: Las seis que daban cero en 0.32.0.
DIAGNOSTICOS = [
    "me diagnosticaron depresión mayor",
    "diagnosed with major depression, on therapy",
    "tengo anorexia desde los 15",
    "tengo bulimia",
    "borderline personality disorder diagnosis",
    "sufro ansiedad generalizada diagnosticada",
]

#: Las cuatro que deben SEGUIR en cero: ansiedad y depresión sin marcador.
COLOQUIALES = [
    "ando bien deprimida esta semana",
    "me da mucha ansiedad hablar en público",
    "tengo ansiedad",
    "esa película me dio ansiedad",
    "tengo depresión",
]


@pytest.mark.parametrize("frase", DIAGNOSTICOS)
def test_el_diagnostico_puntua_tres_en_el_eje_cronico(frase: str):
    s = CHRONIC.score([frase])
    assert s.score == 3, f"{frase!r}: score={s.score}, matched={s.matched}"
    assert s.matched == ("named_diagnosis",)


@pytest.mark.parametrize("frase", COLOQUIALES)
def test_sin_marcador_la_palabra_no_cuenta(frase: str):
    """"Depresión" y "ansiedad" se dicen de pasada; sólo el diagnóstico pesa."""
    s = CHRONIC.score([frase])
    assert s.score == 0 and not s.matched, f"{frase!r} puntuó sin marcador: {s.matched}"


@pytest.mark.parametrize(
    "frase",
    ["me diagnosticaron depresión", "sufro de depresión", "depresión mayor diagnosticada",
     "diagnosed with GAD last year", "me diagnosticaron ansiedad generalizada"],
)
def test_con_marcador_cuenta_en_cualquier_orden(frase: str):
    assert CHRONIC.score([frase]).matched == ("named_diagnosis",)


def test_el_mismo_diagnostico_pesa_igual_en_los_dos_idiomas():
    es = CHRONIC.score(["me diagnosticaron trastorno límite"])
    en = CHRONIC.score(["borderline personality disorder"])
    assert es.score == en.score == 3
    assert es.matched == en.matched == ("named_diagnosis",)


def test_un_diagnostico_solo_no_cruza_el_umbral():
    """Peso 3 contra umbral 4: nombrar un diagnóstico es una mención, no un
    cluster. Es la razón por la que no valía la pena partir el grupo."""
    for frase in DIAGNOSTICOS:
        assert not CHRONIC.score([frase]).crosses, frase


def test_diagnostico_mas_medicacion_si_cruza():
    """El par que el umbral fue diseñado para atrapar, ahora también con depresión."""
    s = CHRONIC.score(["me diagnosticaron depresión mayor", "tomo sertralina"])
    assert s.crosses and set(s.matched) == {"named_diagnosis", "psychiatric_medication"}
