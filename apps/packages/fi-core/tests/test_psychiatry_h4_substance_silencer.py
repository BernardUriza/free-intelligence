"""El silenciador de sustancias del eje de recuperación — la lista de Álex.

Follow-up del H4 (discord-bot #55, 2026-09-15 y 2026-09-21; fi #491). El eje de
recuperación se apaga completo cuando la persona reporta sustancias —"con alguien
en sustancias no se hace intervención, se hace contención"— pero el silenciador
sólo conocía unas cuantas formas de decirlo. Álex midió en fi-core 0.32.0:
*"ando bien pedo"*, *"me tomé unas chelas"*, *"estoy bien pacheco"*, *"estoy
drogado"* y *"tomé mucho alcohol"* dejaban prender la mejoría de alguien
intoxicado — justo el caso para el que el silenciador existe.

Ella produjo la lista completa (discord-bot #55, 2026-09-22 22:14 UTC) y la probó
frase por frase. Esa lista ES la tabla de aceptación de este archivo, copiada tal
cual, con sus dos decisiones:

- Las frases sociales y en pasado (*"me pasé de copas"*, *"me eché unos tragos"*)
  SÍ entran: mejor acompañar de más que dejar escapar a quien la está pasando mal
  pero lo cuenta como fiesta.
- *"vape"* a secas NO entra; sólo *"wax"* y *"pluma de wax"*. Vapear nicotina es
  cotidiano y apagaría el eje de mejoría cada vez que alguien lo mencione.

Y su regla de forma: todas deben ir con "ando / estoy / andaba / estaba", para que
no dependa de cuál cópula usó la persona — el patrón ya lo hacía con "borracho";
le faltaba con "pedo" y "pacheco".
"""

from __future__ import annotations

import pytest

from fi_core.cognitive.psychiatry_signals import (
    PSYCH_CHRONIC_SIGNALS as CHRONIC,
    PSYCH_RECOVERY_SIGNALS as RECOVERY,
)

#: El mensaje de mejoría que SIN sustancias cruza de sobra (3 + 3 sobre 4).
MEJORIA = "ya estoy mejor, ya le hablé a mi hermana"

#: La lista de Álex, verbatim. 18 de alcohol, 8 de mota y otras.
ALCOHOL = [
    "ando pedo",
    "ando bien pedo",
    "estoy pedo",
    "ando de peda",
    "salí de peda",
    "ando en la peda",
    "me tomé unas chelas",
    "me eché unos tragos",
    "me pasé de copas",
    "estoy bien tomado",
    "ando en el pisto",
    "andamos de chupe",
    "ando en el chupe",
    "ya me acabé la botella",
    "tomé mucho alcohol",
    "llevo tres días tomando",
    "soy malacopa",
    "ando cruzado",
]
MOTA_Y_OTRAS = [
    "ando pacheco",
    "estoy pacheco",
    "estoy bien pacheco",
    "fumé mota",
    "ando fumado",
    "estoy drogado",
    "wax",
    "pluma de wax",
]
#: "Estas ya prenden y no hay que tocarlas."
REGRESION = [
    "estoy borracho",
    "me metí coca",
    "ando crudo",
    "me puse hasta atrás",
    "me drogué",
    "me metí unas pastis",
]


def test_el_control_cruza_sin_sustancias():
    s = RECOVERY.score([MEJORIA])
    assert s.crosses and not s.silenced


@pytest.mark.parametrize("frase", ALCOHOL + MOTA_Y_OTRAS)
def test_la_lista_de_alex_silencia_el_eje(frase: str):
    """Las 26. Cada una, junto a un mensaje de mejoría que solo cruzaría, apaga
    el eje a cero y dice por qué."""
    s = RECOVERY.score([f"{MEJORIA}, {frase}"])
    assert s.score == 0 and not s.crosses, f"{frase!r} dejó prender la mejoría: score={s.score}"
    assert "substance_use" in s.silenced, f"{frase!r} apagó el eje sin decir por qué"


@pytest.mark.parametrize("frase", REGRESION)
def test_las_que_ya_prendian_siguen_prendiendo(frase: str):
    s = RECOVERY.score([f"{MEJORIA}, {frase}"])
    assert s.score == 0 and "substance_use" in s.silenced


@pytest.mark.parametrize("copula", ["ando", "estoy", "andaba", "estaba", "andamos"])
@pytest.mark.parametrize("estado", ["pedo", "peda", "bien pedo", "pacheco", "drogado", "tomado", "borracho", "crudo"])
def test_la_copula_es_libre(copula: str, estado: str):
    """Su regla de forma: el estado manda, no la cópula con que lo dijo."""
    s = RECOVERY.score([f"{MEJORIA}, {copula} {estado}"])
    assert "substance_use" in s.silenced, f"{copula} {estado!r} no silenció"


@pytest.mark.parametrize(
    "texto",
    [
        f"{MEJORIA}, uso vape",
        f"{MEJORIA}, ando vapeando",
        f"{MEJORIA}, ando pedaleando",
        f"{MEJORIA}, estoy en la terapia",
        f"{MEJORIA}, estoy bien",
    ],
)
def test_lo_que_no_es_sustancia_no_apaga_el_eje(texto: str):
    """"vape" a secas queda fuera por decisión de Álex; el resto son los
    vecinos léxicos que el patrón nuevo podría haber arrastrado."""
    s = RECOVERY.score([texto])
    assert not s.silenced, f"{texto!r} apagó el eje sin sustancia: {s.silenced}"
    assert s.crosses


def test_el_registro_clinico_sigue_puntuando_en_el_eje_cronico():
    """El silenciador no le quita la comorbilidad al eje crónico: el patrón
    clínico que ahí vive ("alcoholismo", "consumo problemático") sigue dando 2."""
    s = CHRONIC.score(["tiene un consumo problemático de alcohol"])
    assert s.score == 2 and s.matched == ("substance_use",)
