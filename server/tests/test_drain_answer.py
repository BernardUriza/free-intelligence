"""What the model said on its way to a tool is not what it said to the caller.

Measured 2026-09-09, in Discord's #general, in front of two people:

    Task tracking not needed — single-turn action. Proceeding to soft-delete
    fact 73.Hecho, amix. Fact 73 soft-deleted.

The first sentence is the model answering a `<system-reminder>` the SDK injects
about task tracking. It is meta-plumbing, addressed to the harness, and it left
with the reply because `_on_assistant` appends EVERY `TextBlock` to `parts` and
the result joins them with no separator — hence `fact 73.Hecho` welded together.

A sweep of the consumer's whole message history (~15,900 rows) found six such
messages, 2026-05-22 through 2026-09-09, four of them in the last three days.
Not a regression: structural since before AIRE. What changed is frequency — a
turn needs a tool call to produce one, and the personas got their memory tools
back on 2026-08-28.

`answer` is the fix: the text after the LAST tool call. `text` stays exactly as
it was, because accounting and auditing want the whole turn.
"""

from dataclasses import dataclass, field
from typing import Any

import pytest

from aire.engine.drain import drain


@dataclass
class TextBlock:
    text: str


@dataclass
class ToolUseBlock:
    name: str = "mcp__persona_memory__get_agent_facts"
    input: dict[str, Any] | None = None
    id: str = "t1"


@dataclass
class ToolResultBlock:
    tool_use_id: str = "t1"
    is_error: bool | None = None


@dataclass
class AssistantMessage:
    content: list[Any]
    model: str = "claude-opus-4-7"
    usage: dict[str, Any] | None = None
    message_id: str | None = None


@dataclass
class UserMessage:
    content: list[Any] = field(default_factory=list)


@dataclass
class ResultMessage:
    subtype: str = "success"
    usage: dict[str, Any] | None = None
    total_cost_usd: float | None = 0.0
    session_id: str = "s1"


@dataclass
class _Client:
    """El shape que `drain` consume — mismo stub que `test_drain_budget_cut`."""

    messages: list[Any] = field(default_factory=list)

    async def receive_response(self):
        for m in self.messages:
            yield m


async def _drain(messages) -> Any:
    result = None
    async for ev in drain(_Client(messages)):
        if ev.get("type") == "result":
            result = ev["result"]
    assert result is not None
    return result


@pytest.mark.asyncio
async def test_the_answer_excludes_what_was_said_before_a_tool_call():
    """El caso fundador, verbatim."""
    result = await _drain([
        AssistantMessage(content=[
            TextBlock("Task tracking not needed — single-turn action. Proceeding to soft-delete fact 73."),
            ToolUseBlock(),
        ]),
        UserMessage(content=[ToolResultBlock()]),
        AssistantMessage(content=[TextBlock("Hecho, amix. Fact 73 soft-deleted.")]),
        ResultMessage(),
    ])
    assert result.answer == "Hecho, amix. Fact 73 soft-deleted."
    assert "Task tracking" not in result.answer


@pytest.mark.asyncio
async def test_text_still_carries_the_whole_turn():
    """RESISTENCIA: `text` no cambia. Quien contabiliza o audita el turno entero
    —el ledger, los guards, la telemetría— lo sigue leyendo igual, y un fix de
    presentación no tiene por qué borrarle evidencia a nadie."""
    result = await _drain([
        AssistantMessage(content=[TextBlock("Voy a consultar."), ToolUseBlock()]),
        UserMessage(content=[ToolResultBlock()]),
        AssistantMessage(content=[TextBlock("Listo.")]),
        ResultMessage(),
    ])
    assert result.text == "Voy a consultar.Listo."
    assert result.answer == "Listo."


@pytest.mark.asyncio
async def test_a_turn_without_tools_answers_exactly_what_it_said():
    """RESISTENCIA, y es la mayoría de los turnos: sin tool call no hay nada que
    recortar, así que `answer` y `text` coinciden. Si esto se rompe, el fix está
    comiéndose respuestas normales."""
    result = await _drain([
        AssistantMessage(content=[TextBlock("Bebe, aquí sigo.")]),
        ResultMessage(),
    ])
    assert result.answer == result.text == "Bebe, aquí sigo."


@pytest.mark.asyncio
async def test_only_the_last_tool_call_marks_the_boundary():
    """Varias tools seguidas: lo que cuenta es la ÚLTIMA. Todo lo dicho entre
    llamadas sigue siendo camino, no respuesta."""
    result = await _drain([
        AssistantMessage(content=[TextBlock("Primero busco."), ToolUseBlock(id="t1")]),
        UserMessage(content=[ToolResultBlock(tool_use_id="t1")]),
        AssistantMessage(content=[TextBlock("Ahora confirmo."), ToolUseBlock(id="t2")]),
        UserMessage(content=[ToolResultBlock(tool_use_id="t2")]),
        AssistantMessage(content=[TextBlock("Confirmado: no queda nada.")]),
        ResultMessage(),
    ])
    assert result.answer == "Confirmado: no queda nada."
    assert "Primero busco." in result.text and "Ahora confirmo." in result.text


@pytest.mark.asyncio
async def test_a_turn_that_ends_on_a_tool_leaves_the_answer_empty():
    """RESISTENCIA, y es la que obliga al consumidor a tener fallback: si el
    modelo termina llamando una tool y no dice nada después, `answer` queda
    vacío. Eso NO puede leerse como "no hubo respuesta" — `text` sigue teniendo
    lo que dijo, y quien le habla a un humano debe caer ahí antes que quedarse
    mudo. La regla del consumidor es `answer or text`, nunca `answer` a secas."""
    result = await _drain([
        AssistantMessage(content=[TextBlock("Déjame revisar."), ToolUseBlock()]),
        UserMessage(content=[ToolResultBlock()]),
        ResultMessage(),
    ])
    assert result.answer == ""
    assert result.text == "Déjame revisar."
