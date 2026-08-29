"""La superficie de capacidad del runner está ACOTADA, y los tests lo demuestran.

Este archivo sobrevivió a la consolidación en AIRE (2026-08-29) porque su
invariante sobrevivió — lo que cambió es QUIÉN lo ejerce.

ANTES (ruta claude-code, borrada): el peligro era `ClaudeAgentOptions.tools`
sin setear, que le daba al modelo el preset COMPLETO de Claude Code menos un
denylist — y un denylist es una foto: olvida lo que todavía no existía. En
discord-bot, esa misma forma de bug dejó que un turno real de producción llamara
`Bash` cinco veces. `BackendAcotado` fijaba la lista y verificaba en cada
construcción.

AHORA: los builtins ya no los elige este proceso. Los gobierna el dial de modos
de la puerta de AIRE (`complete` no concede ninguno; `agent` concede
Read/Write/Glob/Grep/WebSearch/WebFetch, jaulados a la casita del chat, y en
NINGÚN modo existe Bash). Lo que sí sigue eligiendo este archivo es qué tools
del registry pide cada runner — y ahí estaba el agujero que estos tests cierran:
`registry_tools` estaba HARDCODEADO a las tres, así que un consumer que pedía
menos las recibía todas igual.
"""

from __future__ import annotations

import pytest

from runner import CAPACIDADES_POR_DEFECTO, MODO_AIRE_POR_DEFECTO, build_runner


def test_un_runner_normal_pide_las_capacidades_por_defecto() -> None:
    assert set(build_runner().backend.registry_tools) == set(CAPACIDADES_POR_DEFECTO)


def test_un_consumer_que_pide_MENOS_recibe_menos() -> None:
    """El agujero que este archivo existe para cerrar.

    El tutor del cibercafé de fenix pide `capabilities=["task_tracker"]`
    justamente para NO heredar `rag_store`, que expone
    ingest/delete_document/delete_corpus sobre el corpus del negocio. En la ruta
    AIRE ese acotamiento se perdía en silencio: `_backend_aire` mandaba las tres
    sin mirar lo que el caller pidió, así que una superficie a la que le escriben
    niños podía leer, envenenar o borrar el activo del que depende cotizar."""
    tutor = build_runner(persona_text="tutor de prueba", capabilities=["task_tracker"])
    assert tutor.backend.registry_tools == ("task_tracker",)
    assert "rag_store" not in tutor.backend.registry_tools


@pytest.mark.parametrize("peligrosa", ["rag_store", "persona"])
def test_una_capability_no_pedida_no_se_cuela(peligrosa: str) -> None:
    acotado = build_runner(persona_text="p", capabilities=["task_tracker"])
    assert peligrosa not in acotado.backend.registry_tools


def test_una_lista_vacia_explicita_no_pide_ninguna() -> None:
    """`None` = los defaults; `[]` = ninguna. La distinción es la que permite
    a un consumer pedir CERO tools sin que el default se le cuele por detrás."""
    assert build_runner(persona_text="p", capabilities=[]).backend.registry_tools == ()


def test_los_MCP_locales_no_se_levantan() -> None:
    """`Runner.capabilities` spawnea servidores MCP LOCALES por stdio, y ésos no
    cruzan la puerta. Dejarlos poblados levantaría subprocesos que nadie
    consulta — el turno los pide por NOMBRE al registry de AIRE."""
    runner = build_runner()
    assert runner.capabilities == []
    assert runner.extra_mcp_servers == []


def test_el_modo_por_defecto_no_concede_builtins() -> None:
    """`complete` es lo que og118 quiere: la persona y las tools del registry,
    sin el paquete de builtins del preset `agent`."""
    assert MODO_AIRE_POR_DEFECTO == "complete"
    assert build_runner().backend.default_mode == "complete"


def test_el_tutor_puede_subir_a_agent_sin_arrastrar_a_los_demas() -> None:
    """La búsqueda en internet es load-bearing para el tutor (media persona suya
    es traer un dato real y citarlo). El modo se pide POR RUNNER, así que
    subirlo no toca al mostrador ni a og118."""
    tutor = build_runner(persona_text="tutor", capabilities=["task_tracker"], aire_mode="agent")
    assert tutor.backend.default_mode == "agent"
    assert build_runner().backend.default_mode == "complete"
