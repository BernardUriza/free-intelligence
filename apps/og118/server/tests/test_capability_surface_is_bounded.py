"""La superficie de builtins del runner está ACOTADA por lista, y los tests lo
demuestran en las dos direcciones.

En el Claude Agent SDK, `allowed_tools` gobierna el PERMISO (cuáles corren sin
preguntar) y `tools` gobierna la DISPONIBILIDAD (cuáles existen en el contexto
del modelo). `fi_runner.ClaudeCodeBackend.build_options` nunca setea `tools`,
así que sin el `BackendAcotado` de runner.py el modelo hereda el preset completo
de Claude Code menos el denylist de `ToolPolicy.companion()` — y un denylist es
una foto: olvida lo que todavía no existía. El contenedor tiene ingress público
y carga en el env `CLAUDE_CODE_OAUTH_TOKEN` (el OAuth Max compartido por la
flota), `OG118_ACCESS_TOKEN` y las llaves de TTS/STT. En discord-bot, la misma
forma de bug (sin denylist) dejó que un turno real de producción llamara `Bash`
cinco veces.

Se afirma también lo que SOBREVIVE al cerco: WebSearch/WebFetch son load-bearing
para el tutor del cibercafé (apps/fenix corre este mismo build_runner), y las
tools MCP (task_tracker, rag_store) no son builtins, así que `tools` no las toca.
"""

from __future__ import annotations

import pytest

from fi_runner import COMPANION_BLOCKED_BUILTINS
from runner import (
    BUILTINS_DISPONIBLES,
    _verificar_superficie_acotada,
    build_runner,
)


def _options(runner):
    return runner.backend.build_options(
        system_prompt=runner.persona,
        mcp_servers=[],
        tool_policy=runner.tool_policy,
    )


def test_la_disponibilidad_es_lista_explicita_no_el_preset() -> None:
    """`tools=None` significa el preset entero. Nunca debe salir en None."""
    options = _options(build_runner())
    assert isinstance(options.tools, list), (
        "tools quedó sin setear: el modelo recibe el preset completo de Claude Code"
    )
    assert set(options.tools) == set(BUILTINS_DISPONIBLES)


@pytest.mark.parametrize("prohibida", sorted(COMPANION_BLOCKED_BUILTINS))
def test_ningun_builtin_bloqueado_es_alcanzable(prohibida: str) -> None:
    """Ni disponible ni auto-aprobada: las dos capas, porque fallan al revés."""
    options = _options(build_runner())
    assert prohibida not in (options.tools or [])
    assert prohibida in (options.disallowed_tools or [])
    assert prohibida not in (options.allowed_tools or [])


def test_los_builtins_del_tutor_sobreviven_al_cerco() -> None:
    """El cerco no puede comerse WebSearch/WebFetch: el tutor del cibercafé
    (fenix, «CUANDO BUSCAS EN INTERNET») depende de ellos y comparte runtime."""
    tutor = build_runner(
        persona_text="tutor de prueba",
        capabilities=["task_tracker"],
        extra_mcp_servers=[],
    )
    options = _options(tutor)
    for necesaria in BUILTINS_DISPONIBLES:
        assert necesaria in options.tools


class _OpcionesFalsas:
    def __init__(self, tools):
        self.tools = tools
        self.allowed_tools: list[str] = []
        self.disallowed_tools: list[str] = list(COMPANION_BLOCKED_BUILTINS)


def test_el_guard_rechaza_una_superficie_sin_acotar() -> None:
    """Si alguien vuelve a dejar `tools` en None, el runner revienta al construir."""
    with pytest.raises(RuntimeError, match="preset completo"):
        _verificar_superficie_acotada(_OpcionesFalsas(None))


def test_el_guard_rechaza_un_builtin_prohibido_colado() -> None:
    """Y si alguien mete Bash de vuelta en la lista de disponibles."""
    with pytest.raises(RuntimeError, match="prohibidos"):
        _verificar_superficie_acotada(_OpcionesFalsas([*BUILTINS_DISPONIBLES, "Bash"]))
