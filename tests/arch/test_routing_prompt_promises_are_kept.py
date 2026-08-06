"""Lo que el prompt de ruteo PROMETE tiene que existir en el código.

El 2026-08-06 se encontraron TRES instancias del mismo defecto de clase en un
solo día, todas en el mismo prompt (`demux_ai/prompts/host_routing.md`):

1. **RULE 1 — CONTINUATION HOLDS THE FLOOR**, la regla de MÁXIMA prioridad, iba
   condicionada a "when a recent-conversation block is provided" — y ese bloque
   no llegaba nunca (`_fetch_router_context` murió en 2f8d9ad y el host nuevo no
   lo replantó). Siete líneas de criterio y 5 de 17 ejemplos, letra muerta.
2. **`recovered_without_context`** (bf67e08) reintentaba sin contexto cuando el
   filtro de Azure rechazaba el prompt — imposible de alcanzar, porque nunca
   había contexto que quitar.
3. **`effort`**: el prompt le pedía al modelo una estimación y le aseguraba que
   "this sets how long the persona is given to work", y el valor no tenía UN
   SOLO consumidor. El prompt le mentía al modelo sobre una consecuencia
   inexistente. **Borrado el mismo día** (v4.32.30) en vez de parkeado: un valor
   sin consumidor es deuda, no una feature en pausa ([[migrations-end-with-deletion]]).
   Si vuelve, vuelve CON su consumidor en el mismo PR.

Ninguna de las tres se veía en producción: el log decía `llm_insult` (clean
match) en cada turno, que se lee como salud. Son primas del arnés
`test_every_counted_event_has_a_live_emitter` (contadores escuchando eventos sin
emisor) y de [[migrations-end-with-deletion]]: la promesa sobrevive al mecanismo
que la cumplía, y nadie se entera porque nada se pone rojo.

Este arnés cierra la clase: si el prompt lo pide, el código lo provee o lo
consume — demostrablemente, en CI.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from demux_ai import dispatch, host_loop, llm_shadow_router
from demux_ai.llm_shadow_router import _VALID_TARGETS

PROMPT = Path(__file__).resolve().parents[2] / "demux_ai" / "prompts" / "host_routing.md"


@pytest.fixture(scope="module")
def prompt_text() -> str:
    return PROMPT.read_text(encoding="utf-8")


def test_the_prompt_exists_where_the_router_loads_it_from():
    assert PROMPT.is_file(), f"el router carga {PROMPT.name} en runtime; sin él no hay ruteo"


def test_if_the_prompt_asks_for_a_conversation_block_someone_must_provide_it(prompt_text: str):
    """La promesa #1. El prompt condiciona su regla de máxima prioridad a que
    llegue un bloque de conversación reciente; entonces el host TIENE que
    construirlo y pasarlo. Si esta prueba se pone roja, RULE 1 volvió a ser
    letra muerta y el ruteo perdió las continuaciones sin avisar."""
    if "recent-conversation block" not in prompt_text:
        pytest.skip("el prompt ya no promete un bloque de conversación")

    assert hasattr(host_loop.HostDispatchLoop, "context_for"), (
        "el prompt promete contexto pero el host no sabe construirlo"
    )
    tick_src = inspect.getsource(host_loop.HostDispatchLoop.tick)
    assert "context=" in tick_src, "el host construye contexto pero NO se lo pasa al cerebro — la promesa sigue rota"

    signature = inspect.signature(dispatch.route_and_dispatch)
    assert "context" in signature.parameters, "route_and_dispatch no acepta contexto"


def test_the_effort_estimate_stays_deleted_on_both_sides(prompt_text: str):
    """La promesa #3, ahora en su forma de guardia contra el regreso a medias.

    El effort se borró de los DOS lados el 2026-08-06: la sección del prompt y el
    campo del código. La falla que este test previene es que vuelva por uno solo
    — que alguien reponga la sección del prompt (barato: es un `.md` hot-reload)
    sin consumidor, y el modelo vuelva a gastar razonamiento en un valor que se
    tira. Si vuelve, vuelve COMPLETO: prompt + parser + un consumidor real, en el
    mismo PR."""
    asks_for_effort = "effort" in prompt_text.lower()
    parses_effort = "effort" in inspect.getsource(llm_shadow_router).lower().replace("``effort``", "")
    reaches_telemetry = "effort" in inspect.getsource(dispatch)

    if not asks_for_effort:
        assert not parses_effort, "el prompt ya no pide effort pero el código lo sigue parseando — código muerto"
        return
    assert reaches_telemetry or parses_effort, (
        "el prompt volvió a pedirle un effort al modelo, prometiéndole que define su tiempo "
        "de trabajo, pero el código no lo consume ni lo observa — la mentira de 2026-08-06 regresó"
    )


@pytest.mark.parametrize("target", _VALID_TARGETS)
def test_every_valid_target_is_named_in_the_prompt(target: str, prompt_text: str):
    """Un target que el parser acepta pero el prompt no describe es una persona
    que el cerebro no puede elegir jamás — silenciosamente inalcanzable."""
    assert target in prompt_text.lower(), f"'{target}' es un target válido pero el prompt no se lo presenta al modelo"


def test_the_context_window_is_the_same_number_the_eval_measures():
    """El eval offline (`scripts/router_eval.py`) mide el ruteo con N mensajes de
    contexto. Si producción usa otro N, el eval mide otro sistema y su veredicto
    no aplica — el propio docstring del eval lo advierte."""
    eval_src = (Path(__file__).resolve().parents[2] / "scripts" / "router_eval.py").read_text(encoding="utf-8")
    assert f"ROUTER_CONTEXT_MESSAGES = {host_loop.CONTEXT_MESSAGES}" in eval_src, (
        f"prod usa {host_loop.CONTEXT_MESSAGES} mensajes de contexto y el eval usa otro número"
    )
    assert f"[:{host_loop.CONTEXT_LINE_CHARS}]" in eval_src, (
        f"prod corta cada línea a {host_loop.CONTEXT_LINE_CHARS} chars y el eval corta a otra medida"
    )
