"""Un evento que alguien manda buscar tiene que tener quién lo emita (issue #77).

El guardián que este repo llevaba citando tres veces sin escribirlo nunca. La
frase de Bernard es el porqué entero: **"un test citado sin código detrás es una
promesa que miente al que lee el repo."**

Es el hermano grande de `test_crisis_band_events_have_live_emitters.py`, que
cubre sólo los dos eventos de banda del #54. Éste lo envuelve: recorre TODA la
familia de eventos que el repo manda buscar y verifica que cada uno exista de
verdad en el código.

**La lista no se teclea, se deriva** (decisión de alcance de Bernard, 2026-09-22).
Una lista declarada es un registro congelado: el día que alguien documente un
evento nuevo en una regla y se le olvide agregarlo a la lista, el arnés sigue
verde — que es exactamente el defecto que este arnés existe para matar, así que
no puede tenerlo él mismo. Los consumidores son dos:

1. **`scripts/`** — lo que las herramientas de diagnóstico filtran por nombre.
2. **`.claude/rules/*.md`** — los bloques KQL **y la prosa**. La prosa ES un
   consumidor: es lo que un humano va a buscar en KQL cuando algo truena. Un
   evento nombrado ahí y muerto en el código manda a esa persona a buscar un
   silencio y a leerlo como salud.

Para leer la prosa sin falsos positivos se usa la convención de nombres que ya
existe: un token entre backticks que empieza con una familia de emisor es un
evento; `has_context` o `prev_target` no lo son.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

#: Los paquetes vivos post-purga. Un emisor fuera de aquí no llega a producción.
PAQUETES_VIVOS = ("persona_gateway", "persona_runner", "khimeras_shared", "demux_ai", "shared")

#: Los métodos de structlog que publican un evento.
NIVELES = frozenset({"debug", "info", "warning", "warn", "error", "exception", "critical", "msg"})

#: Los nombres con los que este repo liga su logger.
LOGGERS = frozenset({"log", "logger", "LOG", "_log"})

#: Un token entre backticks que empieza así es un evento, no un campo. La
#: convención ya existía; esto sólo la lee.
FAMILIAS = ("host_", "persona_gateway_", "agent_runner_", "aire_route_", "crisis_band_")

#: Excepciones nombradas, cada una con su porqué. Va a mano a propósito: es
#: corta y cada línea se justifica. Una excepción sin razón escrita es la lista
#: congelada entrando por la puerta de atrás.
EXCEPCIONES: dict[str, str] = {}

#: Si el extractor se rompe y no encuentra nada, TODO pasa y el arnés se vuelve
#: decorativo — la misma clase de cero que se lee como salud. Este piso es lo
#: que hace que el arnés pueda sonar.
MINIMO_DE_EVENTOS_CITADOS = 15

_EVENTO_EN_FILTRO = (
    re.compile(r"""tostring\(p\.event\)\s*==\s*['"]([a-z0-9_]+)['"]"""),
    re.compile(r"""p\.event\s*==\s*['"]([a-z0-9_]+)['"]"""),
    re.compile(r"""\bev\s*==\s*['"]([a-z0-9_]+)['"]"""),
)
_EVENTO_EN_LISTA = re.compile(r"""\bev\s+in\s*\(([^)]*)\)""")
_CADENA = re.compile(r"""['"]([a-z0-9_]+)['"]""")
_TOKEN_EN_BACKTICKS = re.compile(r"`([a-z0-9_]+)`")


def eventos_emitidos() -> set[str]:
    """Los nombres que el código vivo de verdad publica.

    Estático (`ast`) y no por ejecución, igual que el arnés del #54: así corre
    en una máquina sin fi-core instalado. Cuenta dos formas, que son las dos que
    este repo usa: el nombre como primer argumento de `log.<nivel>(...)`, y la
    constante `*_EVENT = "<nombre>"`.
    """
    emitidos: set[str] = set()
    for paquete in PAQUETES_VIVOS:
        for archivo in (REPO / paquete).rglob("*.py"):
            try:
                arbol = ast.parse(archivo.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - un archivo roto no calla el arnés
                continue
            for nodo in ast.walk(arbol):
                emitidos |= _nombre_en_llamada_al_log(nodo) | _nombre_en_constante(nodo)
    return emitidos


def _nombre_en_llamada_al_log(nodo: ast.AST) -> set[str]:
    """`log.info("persona_gateway_turn_failed", …)` → el nombre del evento."""
    if not (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)):
        return set()
    base = nodo.func.value
    es_logger = nodo.func.attr in NIVELES and isinstance(base, ast.Name) and base.id in LOGGERS
    if not (es_logger and nodo.args and isinstance(nodo.args[0], ast.Constant)):
        return set()
    return {nodo.args[0].value} if isinstance(nodo.args[0].value, str) else set()


def _nombre_en_constante(nodo: ast.AST) -> set[str]:
    """`CLASSIFIED_EVENT = "crisis_band_classified"` → el nombre del evento."""
    if not (isinstance(nodo, ast.Assign) and isinstance(nodo.value, ast.Constant)):
        return set()
    if not isinstance(nodo.value.value, str):
        return set()
    nombra_evento = any(isinstance(d, ast.Name) and d.id.endswith("_EVENT") for d in nodo.targets)
    return {nodo.value.value} if nombra_evento else set()


def eventos_citados() -> dict[str, set[str]]:
    """Los nombres que los consumidores mandan buscar, con quién los cita.

    El valor es el conjunto de archivos que lo nombran, para que el mensaje de
    error diga a quién se le va a mentir cuando el evento no exista.
    """
    citados: dict[str, set[str]] = {}

    def anotar(evento: str, quien: Path) -> None:
        citados.setdefault(evento, set()).add(quien.relative_to(REPO).as_posix())

    directorio_scripts = REPO / "scripts"
    archivos = [*directorio_scripts.rglob("*.py"), *directorio_scripts.rglob("*.sh")]
    archivos += list((REPO / ".claude" / "rules").rglob("*.md"))
    for archivo in archivos:
        texto = archivo.read_text(encoding="utf-8", errors="ignore")
        for patron in _EVENTO_EN_FILTRO:
            for encontrado in patron.finditer(texto):
                anotar(encontrado.group(1), archivo)
        for lista in _EVENTO_EN_LISTA.finditer(texto):
            for cadena in _CADENA.finditer(lista.group(1)):
                anotar(cadena.group(1), archivo)
        if archivo.suffix == ".md":
            for token in _TOKEN_EN_BACKTICKS.finditer(texto):
                if token.group(1).startswith(FAMILIAS):
                    anotar(token.group(1), archivo)
    return citados


def test_every_counted_event_has_a_live_emitter():
    """El guardián del #77: nada se manda buscar sin que alguien lo emita.

    Éste es el nombre que `test_routing_prompt_promises_are_kept.py`,
    `test_crisis_band_events_have_live_emitters.py` y
    `.claude/rules/router-observability.md` llevaban citando desde el #54.
    """
    citados = eventos_citados()
    emitidos = eventos_emitidos()

    huerfanos = {
        evento: sorted(quienes)
        for evento, quienes in citados.items()
        if evento not in emitidos and evento not in EXCEPCIONES
    }

    assert not huerfanos, (
        "estos eventos se mandan buscar y nadie los emite — quien los busque en KQL "
        "va a encontrar un silencio y lo va a leer como salud:\n"
        + "\n".join(f"  - {evento!r} citado en {quienes}" for evento, quienes in sorted(huerfanos.items()))
    )


def test_el_arnes_puede_sonar():
    """Un arnés que no encuentra nada que cuidar pasa siempre y no cuida nada.

    La misma trampa que la regla del repo nombra: *"antes de leer un cero como
    salud, pregunta: si esto estuviera roto ahora mismo, ¿este contador podría
    subir?"*. Si el extractor se rompe —un `rglob` que ya no encuentra, una
    convención que cambió— la lista queda vacía y el test de arriba pasa verde
    sin haber mirado nada.
    """
    citados = eventos_citados()
    assert len(citados) >= MINIMO_DE_EVENTOS_CITADOS, (
        f"sólo se derivaron {len(citados)} eventos citados y el piso es "
        f"{MINIMO_DE_EVENTOS_CITADOS}: el extractor dejó de leer a sus consumidores, "
        "así que el arnés de arriba está pasando sin revisar nada"
    )
    assert eventos_emitidos(), "no se encontró UN solo emisor en los paquetes vivos: el lector de `ast` se rompió"


def test_las_excepciones_traen_su_porque():
    """Una excepción sin razón escrita es la lista congelada por la puerta de atrás."""
    sin_razon = [evento for evento, razon in EXCEPCIONES.items() if not razon.strip()]
    assert not sin_razon, f"estas excepciones no dicen por qué existen: {sin_razon}"
