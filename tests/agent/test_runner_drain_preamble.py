"""`_drain` — the persona speaks its answer, never its plumbing.

Vultur's agenda #1 posted "Necesito cargar mis herramientas de memoria primero
para verificar si hay historial previo, y luego ejecutar la búsqueda.NADA" to
#general (2026-07-25 08:39 UTC): the model's tool preamble fused with its real
answer because every TextBlock of every AssistantMessage was concatenated. That
leak also broke the agenda anti-spam gate, which requires the exact `NADA`.
"""

from __future__ import annotations

from persona_runner.api.turn import _drain


class TextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class ToolUseBlock:
    def __init__(self, name: str, tool_input: dict | None = None) -> None:
        self.name = name
        self.input = tool_input or {}


class AssistantMessage:
    def __init__(self, content: list) -> None:
        self.content = content


def fresh_state() -> dict:
    return {
        "text": "",
        "preamble_chars": 0,
        "tool_calls": [],
        "input_tokens": 0,
        "output_tokens": 0,
        "stop_reason": "",
        "session_uuid": None,
        "model": "",
    }


class TestToolPreambleIsNotTheAnswer:
    def test_the_vultur_leak_no_longer_reaches_the_channel(self):
        state = fresh_state()
        preamble = "Necesito cargar mis herramientas de memoria primero para verificar si hay historial previo, y luego ejecutar la búsqueda."
        _drain(AssistantMessage([TextBlock(preamble), ToolUseBlock("WebSearch", {"query": "x"})]), state)
        _drain(AssistantMessage([TextBlock("NADA")]), state)

        assert state["text"] == "NADA"
        assert state["preamble_chars"] == len(preamble)
        assert [tc["name"] for tc in state["tool_calls"]] == ["WebSearch"]

    def test_tool_calls_are_still_recorded_when_their_text_is_dropped(self):
        state = fresh_state()
        _drain(AssistantMessage([TextBlock("voy a buscar"), ToolUseBlock("Grep", {"pattern": "p"})]), state)

        assert state["text"] == ""
        assert state["tool_calls"] == [{"name": "Grep", "input_keys": ["pattern"]}]

    def test_a_toolless_turn_is_untouched(self):
        state = fresh_state()
        _drain(AssistantMessage([TextBlock("Bb. Yo sigo aquí.")]), state)

        assert state["text"] == "Bb. Yo sigo aquí."
        assert state["preamble_chars"] == 0

    def test_consecutive_final_messages_join_on_a_newline_never_fuse(self):
        state = fresh_state()
        _drain(AssistantMessage([TextBlock("Primera línea.")]), state)
        _drain(AssistantMessage([TextBlock("Segunda línea.")]), state)

        assert state["text"] == "Primera línea.\nSegunda línea."

    def test_a_turn_that_only_narrates_its_plumbing_says_nothing(self):
        state = fresh_state()
        _drain(AssistantMessage([TextBlock("déjame revisar"), ToolUseBlock("Read")]), state)

        assert state["text"] == ""
