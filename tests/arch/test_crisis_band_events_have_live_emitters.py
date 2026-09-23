"""Los eventos de banda no pueden quedarse sin quién los emita (issue #54).

La lección de `.claude/rules/router-observability.md`, en su forma más cara:
`recovered_without_context` fue un contador **inalcanzable** seis semanas. Su
cero no significaba "no pasó", significaba "no puede pasar" — y se leía como
salud. La regla que salió de ahí es textual: *"antes de leer un cero como
salud, pregunta: si esto estuviera roto ahora mismo, ¿este contador podría
subir?"*.

Aplicada a este issue: el día que alguien borre la llamada en el camino del
turno, `khimeras_shared/audit.py` va a seguir ahí completito, sus tests
unitarios van a seguir verdes, y `crisis_band_classified` no va a volver a
aparecer en KQL nunca. **Nada se pondría rojo.** Este arnés es lo que se pone
rojo.

Verifica los TRES eslabones de la cadena, porque romper cualquiera produce el
mismo silencio:

1. el nombre del evento existe como constante,
2. llamar a su emisor produce ESE nombre en el log (no un primo parecido),
3. y ese emisor se llama de verdad desde el camino del turno.

El eslabón 3 va por análisis estático (`ast`) y no por ejecución: así el arnés
corre en una máquina sin fi-core instalado — la de Álex incluida, que es quien
tiene que poder verificar la parte que guarda datos de personas reales en
crisis.

Éste cubre los dos eventos del #54, no la familia entera. El guardián completo
ya existe y lo envuelve: `tests/arch/test_every_counted_event_has_a_live_emitter.py`
(issue #77), que deriva los eventos de sus consumidores en vez de listarlos.
Este arnés se queda porque llega más lejos en los dos eventos que cuida: además
de que exista el emisor, verifica que llamarlo produzca ESE nombre y que el
camino del turno lo llame de verdad.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from khimeras_shared.audit import (
    ABSENT_EVENT,
    CLASSIFIED_EVENT,
    log_crisis_band_absent,
    log_crisis_band_classified,
)

REPO = Path(__file__).resolve().parents[2]

#: El camino del turno: donde estos eventos TIENEN que dispararse.
CAMINO_DEL_TURNO = REPO / "khimeras_shared" / "guidance.py"

UN_VEREDICTO = {
    "band": "HIGH",
    "gravity": 7.0,
    "reasons": ["ideación suicida pasiva"],
    "critical_override": False,
    "signals": ["explicit_ideation"],
    "persona_id": "valentis",
}

#: (nombre del evento, cómo se dispara, nombre del emisor que hay que llamar)
LOS_DOS_EVENTOS = [
    (CLASSIFIED_EVENT, lambda: log_crisis_band_classified(**UN_VEREDICTO), "log_crisis_band_classified"),
    (
        ABSENT_EVENT,
        lambda: log_crisis_band_absent(persona_id="valentis", reason="mensaje_vacio"),
        "log_crisis_band_absent",
    ),
]


def funciones_llamadas_en(ruta: Path) -> set[str]:
    """Los nombres de función que ESE archivo llama de verdad.

    Estático a propósito: importar el módulo arrastraría fi-core, y un arnés
    que sólo corre en el entorno de una persona es medio arnés.
    """
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    return {nodo.func.id for nodo in ast.walk(arbol) if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)}


@pytest.mark.parametrize("evento,disparar,emisor", LOS_DOS_EVENTOS, ids=[e[0] for e in LOS_DOS_EVENTOS])
def test_cada_evento_de_banda_tiene_un_emisor_vivo(evento, disparar, emisor):
    # Eslabón 2 — el emisor emite ESTE nombre, no uno parecido.
    with capture_logs() as capturado:
        disparar()
    emitidos = {e["event"] for e in capturado}
    assert evento in emitidos, f"{emisor}() no emite {evento!r}; emitió {sorted(emitidos)}"

    # Eslabón 3 — y alguien lo llama desde el camino del turno.
    llamadas = funciones_llamadas_en(CAMINO_DEL_TURNO)
    assert emisor in llamadas, (
        f"{evento!r} se quedó sin emisor vivo: nada en "
        f"{CAMINO_DEL_TURNO.relative_to(REPO).as_posix()} llama a {emisor}(). "
        "El evento dejaría de aparecer en KQL y su cero se leería como salud."
    )


def test_el_denominador_se_dispara_por_mas_de_un_camino():
    """Un `absent` con un solo llamador es un denominador a medias.

    Los turnos salen del guardián por varias puertas —mensaje vacío, sin
    guidance, el clasificador caído, el registro caído— y si sólo una de ellas
    cuenta, la tasa se calcula contra un denominador que no incluye a los demás.
    """
    fuente = CAMINO_DEL_TURNO.read_text(encoding="utf-8")
    assert fuente.count("log_crisis_band_absent(") >= 4, (
        "quedan menos salidas contadas de las que el guardián tiene: "
        "algún camino de este archivo devuelve sin contar su turno"
    )
