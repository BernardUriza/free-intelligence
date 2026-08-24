"""OG118-LIVING-CLAUDE — casita-per-chat + the persona tool on the AIRE route.

Cada chat vive en SU casita AIRE (og118-{conversation_id}): app.py setea
AIRE_CHAT_PROJECT por request y AIREBackend la resuelve al tope de cada turno
(project_for_turn). El primer turno de un chat instala la persona base vía
/init (que por contrato de AIRE preserva la parte VIVA del CLAUDE.md), y cada
turno pide la tool `persona` del registry para que el agente lea/evolucione su
identidad viva. Unit/mock only — nada toca la puerta real.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fi_runner import AIREBackend, ToolPolicy

from runner import AIRE_CHAT_PROJECT, aire_project_for_chat, build_runner

# --- naming: og118-{conversation_id}, filtrado al allowlist de AIRE ----------


def test_project_name_prefixes_the_conversation_id() -> None:
    assert aire_project_for_chat("abc-123_XYZ") == "og118-abc-123_XYZ"


def test_project_name_strips_chars_outside_aires_allowlist() -> None:
    assert aire_project_for_chat("a!b c/../d") == "og118-abcd"


def test_project_name_caps_at_aires_128() -> None:
    name = aire_project_for_chat("x" * 200)
    assert name is not None
    assert len(name) == 128
    assert name.startswith("og118-")


def test_no_usable_id_falls_back_to_none() -> None:
    assert aire_project_for_chat(None) is None
    assert aire_project_for_chat("") is None
    assert aire_project_for_chat("!!!") is None


def test_project_name_prefix_follows_the_deploys_base(monkeypatch) -> None:
    """La costura del consumer (aire-server #35): el prefijo del chat es la
    casita base del deploy — fenix nombra `fenix-{chat}` seteando
    OG118_AIRE_PROJECT, sin tocar este runtime."""
    monkeypatch.setenv("OG118_AIRE_PROJECT", "fenix")
    assert aire_project_for_chat("abc") == "fenix-abc"


# --- wiring: la ruta AIRE pide la tool persona y resuelve casita por turno ---


@pytest.fixture
def aire_runner(monkeypatch):
    monkeypatch.setenv("OG118_BACKEND", "aire")
    monkeypatch.delenv("OG118_AIRE_PROJECT", raising=False)
    return build_runner()


def test_aire_route_requests_the_persona_tool(aire_runner) -> None:
    assert isinstance(aire_runner.backend, AIREBackend)
    assert "persona" in aire_runner.backend.registry_tools
    assert aire_runner.backend.project_for_turn == AIRE_CHAT_PROJECT.get


def test_aire_persona_carries_the_living_identity_paragraph(aire_runner, monkeypatch) -> None:
    assert "mcp__persona__read" in aire_runner.persona
    assert "mcp__persona__update" in aire_runner.persona
    # La ruta claude-code no tiene esas tools: prometerlas sería mentirle al modelo.
    monkeypatch.setenv("OG118_BACKEND", "claude-code")
    assert "mcp__persona__" not in build_runner().persona


def test_aire_route_disables_the_flow_narrator(aire_runner) -> None:
    # El narrador es una segunda llamada al mismo backend con OTRO system prompt:
    # en AIRE su /init sobreescribiría la base de la casita del chat.
    assert aire_runner.flow_narrator is None


# --- per-turn routing + payload: casita del chat, tools y mode en el body ----


@pytest.mark.asyncio
async def test_turn_lands_in_the_chats_casita_with_the_persona_tool(aire_runner, monkeypatch) -> None:
    backend = aire_runner.backend
    seen: list[tuple[str, dict[str, Any]]] = []

    async def fake_stream(project: str, session: str, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        seen.append((project, body))
        yield {"type": "result", "result": {"text": "ok"}}

    async def noop_init(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(backend, "gate_url", "https://gate.test")
    monkeypatch.setattr(backend, "auth_token", "tok")
    monkeypatch.setattr(backend, "_stream_events", fake_stream)
    monkeypatch.setattr(backend, "_ensure_prompt", noop_init)

    token = AIRE_CHAT_PROJECT.set(aire_project_for_chat("chat-abc"))
    try:
        async for _ in backend.run_turn_stream(
            system_prompt=aire_runner.persona,
            user_message="hola",
            mcp_servers=[],
            tool_policy=ToolPolicy(),
        ):
            pass
    finally:
        AIRE_CHAT_PROJECT.reset(token)
    async for _ in backend.run_turn_stream(
        system_prompt=aire_runner.persona,
        user_message="hola",
        mcp_servers=[],
        tool_policy=ToolPolicy(),
    ):
        pass

    assert [p for p, _ in seen] == ["og118-chat-abc", "og118"]
    for _, body in seen:
        assert body["tools"] == ["persona", "task_tracker"]
        # Tools en complete (aire-server 5ae8e33): forzar agent regalaría los
        # builtins del preset (Read/Write/WebSearch…) que og118 no quiere.
        assert body["mode"] == "complete"


@pytest.mark.asyncio
async def test_first_turn_of_a_chat_inits_its_casita_once(aire_runner, monkeypatch) -> None:
    """Nacimiento delgado (aire-server ef21e68): la persona compuesta (base +
    constraints + identidad viva) se instala UNA vez en la casita base og118 —
    ANTES del primer chat, porque es la única fuente de la persona — y cada
    casita de chat nace con solo el stub `@base og118` que AIRE dereferencia en
    cada spawn. Dos turnos del mismo chat → un solo init; otro chat → su stub."""
    backend = aire_runner.backend
    posts: list[tuple[str, dict[str, Any]]] = []

    class _Res:
        status_code = 200
        text = "ok"

    class _Client:
        async def post(self, url: str, *, headers: Any = None, json: Any = None) -> Any:
            posts.append((url, json))
            return _Res()

    async def fake_stream(project: str, session: str, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "result", "result": {"text": "ok"}}

    monkeypatch.setattr(backend, "gate_url", "https://gate.test")
    monkeypatch.setattr(backend, "auth_token", "tok")
    monkeypatch.setattr(backend, "_client", _Client())
    monkeypatch.setattr(backend, "_stream_events", fake_stream)

    async def turn(chat: str) -> None:
        token = AIRE_CHAT_PROJECT.set(aire_project_for_chat(chat))
        try:
            async for _ in backend.run_turn_stream(
                system_prompt=aire_runner.persona,
                user_message="hola",
                mcp_servers=[],
                tool_policy=ToolPolicy(),
            ):
                pass
        finally:
            AIRE_CHAT_PROJECT.reset(token)

    await turn("chat-1")
    await turn("chat-1")
    await turn("chat-2")

    assert [u for u, _ in posts] == [
        "https://gate.test/projects/og118/init",
        "https://gate.test/projects/og118-chat-1/init",
        "https://gate.test/projects/og118-chat-2/init",
    ]
    base_body = posts[0][1]
    assert base_body["claude_md"] == aire_runner.persona.strip()
    assert "mcp__persona__update" in base_body["claude_md"]
    for _, body in posts[1:]:
        assert body == {"claude_md": "@base og118"}
