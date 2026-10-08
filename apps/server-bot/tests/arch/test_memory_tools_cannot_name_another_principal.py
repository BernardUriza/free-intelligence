"""Una persona no puede pedir los datos de OTRA persona, ni queriendo.

El 2026-08-10 Unborn Being le dijo a Bernard "el THC que te falló cuando murió
tu madre". La madre de Bernard está viva — es fiadora de su loft, y así consta
en sus propios facts. El fact "Su madre falleció" es de Alex. No fue una
alucinación: fue el modelo escribiendo un `user_id` en el parámetro de una tool.

Las seis tools de `memory_reads` recibían `user_id` / `channel_id` como
argumentos, o sea que la identidad sobre la que operaban la elegía el modelo.
OWASP LLM06 lo llama excessive agency; el paper "Capability Gates Are Not
Authorization" (arXiv 2606.28679) lo llama confused deputy y da la cura en una
frase: *bind the authenticated user's identity from the session context rather
than accepting user identification from the model's tool parameters*.

Validar el parámetro NO era la cura. El id de Alex es un snowflake perfectamente
válido: cualquier `pattern` lo habría dejado pasar. La única defensa que existía
—un `startswith("__")` en `deep_memory`— protegía archivos sintéticos y jamás se
pensó contra otra persona, que resultó ser el agujero real.

Tampoco basta atar el principal al crear la sesión: el pool se llavea por
`channel_id[:persona_id]` y en #general la misma sesión atiende a Bernard y a
Alex. Por eso el binding es por TURNO (`mcp_tools/turn_context.py`).

Este arnés afirma lo que ninguna prueba manual puede: que no queda ni un
parámetro de identidad que el modelo pueda escribir.
"""

from __future__ import annotations

import asyncio

import pytest

from persona_runner.mcp_tools import PERSONA_MEMORY_TOOLS
from persona_runner.mcp_tools.turn_context import (
    NoTurnPrincipalError,
    bind_turn_principal,
    current_principal,
    reset_turn_principal,
)

# Nombres de parámetro que significan "dime de quién hablo" — justo lo que el
# modelo no debe poder decidir.
IDENTITY_PARAMS = {"user_id", "channel_id", "principal_id", "author_id"}

# `agent_facts` es la memoria que una persona tiene sobre SÍ MISMA, llaveada por
# agent_id (la persona), no por un humano. No es identidad de usuario.
SELF_KNOWLEDGE_PARAM = "agent_id"


def _schema_of(tool) -> dict:
    schema = getattr(tool, "input_schema", None) or {}
    if isinstance(schema, dict) and schema.get("type") == "object":
        return schema.get("properties", {}) or {}
    return schema if isinstance(schema, dict) else {}


@pytest.mark.parametrize("tool", PERSONA_MEMORY_TOOLS, ids=lambda t: t.name)
def test_no_memory_tool_takes_a_human_identity_parameter(tool):
    """El modelo no puede nombrar a nadie: no hay dónde escribirlo."""
    params = set(_schema_of(tool).keys()) - {SELF_KNOWLEDGE_PARAM}
    leaked = params & IDENTITY_PARAMS
    assert not leaked, (
        f"{tool.name} todavía acepta {sorted(leaked)} del modelo — "
        f"el principal lo ata el servidor en turn_context, no el LLM"
    )


def test_a_tool_outside_a_bound_turn_fails_loudly_instead_of_guessing():
    """Sin principal atado se cae, porque adivinar es el bug original."""
    with pytest.raises(NoTurnPrincipalError):
        current_principal()


def test_the_bound_principal_is_the_one_the_turn_carries():
    token = bind_turn_principal(user_id="907264175246569543", channel_id="1489180895264116736")
    try:
        principal = current_principal()
        assert principal.user_id == "907264175246569543"
        assert principal.channel_id == "1489180895264116736"
    finally:
        reset_turn_principal(token)


def test_two_concurrent_turns_do_not_see_each_other_principal():
    """El caso que un valor por sesión NO cubre: un canal es multi-usuario.

    Bernard y Alex comparten la sesión de #general, así que el aislamiento tiene
    que sostenerse entre turnos que corren a la vez en el mismo event loop.
    """

    async def turn_for(user_id: str, delay: float) -> str:
        token = bind_turn_principal(user_id=user_id, channel_id="1489180895264116736")
        try:
            await asyncio.sleep(delay)  # deja correr al hermano en medio
            return current_principal().user_id
        finally:
            reset_turn_principal(token)

    async def both() -> list[str]:
        return list(
            await asyncio.gather(
                asyncio.create_task(turn_for("907264175246569543", 0.02)),
                asyncio.create_task(turn_for("1431300030823927999", 0.01)),
            )
        )

    bernard, alex = asyncio.run(both())
    assert bernard == "907264175246569543"
    assert alex == "1431300030823927999"
