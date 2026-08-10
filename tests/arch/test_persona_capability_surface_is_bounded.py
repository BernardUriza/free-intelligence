"""La superficie de capacidad de una persona está ACOTADA, y CI lo demuestra.

El 2026-08-10 se comprobó que un turno real de producción llamó `Bash` cinco
veces. La entrada de ese modelo es lo que cualquiera escriba en Discord, y el
contenedor donde corre lleva `POSTGRES_URL`, `PERSONA_RUNNER_TOKEN` y el token
OAuth Max compartido por los cinco consumidores de la flota — todos legibles con
un `env`.

La causa no fue una tool mal escrita: fue confundir dos conceptos del SDK que se
parecen y no lo son.

- `allowed_tools` gobierna el PERMISO — cuáles no piden confirmación.
- `tools` gobierna la DISPONIBILIDAD — cuáles existen en el contexto del modelo.

`fi_runner.build_options` nunca seteaba `tools`, así que el preset completo de
Claude Code entraba por default, y `permission_mode=BYPASS` aprobaba todo sin
preguntar. El allowlist de dos nombres (`WebSearch`, `WebFetch`) se leía como un
cerco y no cercaba nada. `ToolPolicy.builtin_disallowed` existía desde siempre —
su propio docstring da el ejemplo `["Bash", "Write", "Edit"]  # PHI safety` — y
nadie lo había usado.

Lo que este arnés cierra es la clase, no el caso: una superficie de capacidad que
sólo se afirma por lo que INCLUYE es ciega a lo que hereda. Un preset que mañana
gane una tool con forma de shell entra sola y en silencio. Por eso se afirma en
las dos direcciones, y por eso `browser_evaluate` también está prohibido: JS
arbitrario en el contexto de una página es la misma capacidad que un shell con
otra puerta — un `fetch()` basta para sacar los secretos del env.

Hermano de `test_routing_prompt_promises_are_kept`: lo que el sistema promete
sobre sí mismo, el código lo demuestra o se pone rojo.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from persona_runner.engine.options import (
    FORBIDDEN_BUILTIN_TOOLS,
    PLAYWRIGHT_ALLOWED_TOOLS,
    REQUIRED_BUILTIN_TOOLS,
    build_options,
    verify_required_tools,
)


@pytest.fixture(scope="module")
def options():
    os.environ.setdefault("POSTGRES_URL", "postgresql://test/test")
    return asyncio.run(build_options("persona de prueba"))


def test_availability_is_an_explicit_list_not_the_full_preset(options):
    """`tools=None` significa el preset entero. Nunca debe quedar en None."""
    assert isinstance(options.tools, list), "tools quedó sin setear: el modelo recibe el preset completo de Claude Code"
    assert set(options.tools) == set(REQUIRED_BUILTIN_TOOLS)


@pytest.mark.parametrize("forbidden", FORBIDDEN_BUILTIN_TOOLS)
def test_no_shell_shaped_builtin_is_reachable(options, forbidden):
    """Ni disponible ni auto-aprobada: las dos capas, porque fallan al revés."""
    assert forbidden not in (options.tools or [])
    assert forbidden in (options.disallowed_tools or [])
    assert forbidden not in (options.allowed_tools or [])


def test_browser_evaluate_is_not_a_permitted_playwright_tool():
    """JS arbitrario = shell con otra puerta. Un fetch() saca el env entero."""
    assert "browser_evaluate" not in PLAYWRIGHT_ALLOWED_TOOLS


def test_the_judge_declares_itself_toolless_and_actually_is():
    """El judge decía en un comentario "No tools" y podía alcanzar Bash.

    Corre con `bypassPermissions`, así que `allowed_tools=[]` no lo dejaba sin
    herramientas — sólo sin herramientas PRE-APROBADAS, que bypass aprueba de
    todas formas. La superficie de una utilidad one-shot se declara con
    `tools=[]`, y esto lo demuestra leyendo el código que de verdad corre.
    """
    source = Path(__file__).resolve().parents[2] / "persona_runner" / "api" / "judge.py"
    text = source.read_text(encoding="utf-8")
    assert "tools=[]," in text, "el judge no deshabilita los builtins con tools=[]"


def test_required_builtins_survive_the_lockdown(options):
    """El cerco no puede comerse WebSearch: es load-bearing (2026-06-14)."""
    for required in REQUIRED_BUILTIN_TOOLS:
        assert required in options.tools
        assert required in options.allowed_tools


class _FakeOptions:
    def __init__(self, tools):
        self.allowed_tools = list(REQUIRED_BUILTIN_TOOLS)
        self.tools = tools
        self.disallowed_tools: list[str] = []


def test_guard_rejects_an_unbounded_surface():
    """El guard se pone rojo si alguien vuelve a dejar `tools` en None."""
    with pytest.raises(RuntimeError, match="FULL"):
        verify_required_tools(_FakeOptions(None))


def test_guard_rejects_a_leaked_forbidden_builtin():
    """Y si alguien mete Bash de vuelta en la lista de disponibles."""
    with pytest.raises(RuntimeError, match="forbidden built-ins"):
        verify_required_tools(_FakeOptions([*REQUIRED_BUILTIN_TOOLS, "Bash"]))
