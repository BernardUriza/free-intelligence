"""El host recuerda la conversación y se la pasa al cerebro que rutea.

2026-08-06: `host_routing.md` abre con RULE 1 — CONTINUATION HOLDS THE FLOOR
(highest priority) — condicionada a "when a recent-conversation block is
provided". Ese bloque NUNCA llegaba: `_fetch_router_context` murió con
`personas/` en 2f8d9ad y el host nuevo jamás lo replantó, así que la regla de
máxima prioridad del prompt era inalcanzable en producción y el 97.6% de los
turnos (331/339 en 30 días) caía en insult.

El caso que lo probó en vivo, #general 14:42 UTC de ese día: tres turnos
seguidos de Insult sobre el extractor del baño, y "explica mejor lo del
extractor 24/7 como línea base" se fue a **frugivoro** (`llm_frugivoro`, clean
match — decisión del modelo, no fallback). Reproducido en banco: sin contexto
→ frugivoro, con contexto → insult.

Regla de mutador: positivo (el contexto llega con el formato canónico y en
orden) + resistencia (un nickname de guild jamás sustituye al nombre del
registry; sin conversación se rutea SIN bloque, no con uno vacío).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from demux_ai.host_client import HostClient
from demux_ai.host_loop import CONTEXT_MESSAGES, HostDispatchLoop
from shared.personas.registry import get_persona, persona_id_by_bot_user_id


def _loop(router: object) -> HostDispatchLoop:
    return HostDispatchLoop(router=router)


def _router(target: str = "insult") -> MagicMock:
    r = MagicMock()
    r.route = AsyncMock(return_value=SimpleNamespace(target=target, reason=f"llm_{target}"))
    return r


def test_context_is_the_canonical_block_oldest_first():
    loop = _loop(_router())
    loop.remember(channel_id="C1", author_name="bernard2389", text="ya lo voy a dejar siempre encendido")
    loop.remember(channel_id="C1", author_name="Insult", text="el bypass te quedó limpio")
    assert loop.context_for("C1") == (
        "bernard2389: ya lo voy a dejar siempre encendido\nInsult: el bypass te quedó limpio"
    )


def test_an_empty_channel_routes_without_a_block_not_with_an_empty_one():
    loop = _loop(_router())
    assert loop.context_for("C-nuevo") is None


def test_whitespace_never_becomes_a_context_line():
    loop = _loop(_router())
    loop.remember(channel_id="C1", author_name="bernard2389", text="   \n  ")
    assert loop.context_for("C1") is None


def test_the_window_keeps_only_the_last_n_messages():
    loop = _loop(_router())
    for i in range(CONTEXT_MESSAGES + 5):
        loop.remember(channel_id="C1", author_name="bernard2389", text=f"msg{i}")
    block = loop.context_for("C1")
    assert block is not None
    lines = block.splitlines()
    assert len(lines) == CONTEXT_MESSAGES
    assert lines[0] == f"bernard2389: msg{5}"
    assert lines[-1] == f"bernard2389: msg{CONTEXT_MESSAGES + 4}"


def test_a_long_line_is_capped_like_the_eval_caps_it():
    loop = _loop(_router())
    loop.remember(channel_id="C1", author_name="bernard2389", text="x" * 900)
    assert loop.context_for("C1") == "bernard2389: " + "x" * 300


def test_channels_never_bleed_into_each_other():
    loop = _loop(_router())
    loop.remember(channel_id="C1", author_name="Alex", text="hay que ver peli")
    loop.remember(channel_id="C2", author_name="bernard2389", text="explica lo del extractor")
    assert loop.context_for("C1") == "Alex: hay que ver peli"
    assert loop.context_for("C2") == "bernard2389: explica lo del extractor"


@pytest.mark.asyncio
async def test_the_routing_brain_receives_the_conversation_not_just_the_message():
    """El bug de #general 14:42: sin este bloque, 'explica mejor lo del extractor'
    llega huérfano y el modelo no puede saber que Insult traía el hilo."""
    router = _router()
    loop = _loop(router)
    loop.remember(channel_id="C1", author_name="Insult", text="el 2074 mueve varias veces más aire")
    loop.handle_message(
        channel_id="C1",
        author_id="U1",
        author_is_bot=False,
        text="explica mejor lo del extractor 24/7 como línea base",
        now=100.0,
        author_name="bernard2389",
    )
    await loop.tick(200.0)

    router.route.assert_awaited_once()
    text, context = router.route.await_args.args
    assert text == "explica mejor lo del extractor 24/7 como línea base"
    assert context is not None, "RULE 1 del prompt es inalcanzable sin este bloque"
    assert "Insult: el 2074 mueve varias veces más aire" in context


@pytest.mark.asyncio
async def test_a_persona_reply_is_half_of_what_makes_the_next_message_a_continuation():
    """`handle_message` tira a los bots ANTES de retener nada, así que si el
    contexto se llenara ahí, la voz de la persona jamás entraría — y una
    continuación es, por definición, la respuesta a lo que la persona dijo."""
    router = _router()
    loop = _loop(router)
    assert (
        loop.handle_message(
            channel_id="C1",
            author_id="BOT",
            author_is_bot=True,
            text="soy una persona hablando",
            now=100.0,
        )
        is False
    )
    loop.remember(channel_id="C1", author_name="Frugívoro", text="soy una persona hablando")
    block = loop.context_for("C1")
    assert block is not None
    assert "Frugívoro: soy una persona hablando" in block


def _client(loop: HostDispatchLoop) -> HostClient:
    return HostClient(loop, intents=discord.Intents.none(), stt_client=None)


def test_a_persona_is_named_by_the_registry_never_by_its_guild_nickname():
    """La resistencia que casi se cuela: `Member.display_name` devuelve el
    apodo del servidor ("frugi"), y `host_routing.md` solo mapea el nombre
    canónico ("Frugívoro"). Un apodo en el bloque es un nombre que el cerebro
    no puede resolver — el contexto llegaría degradado en silencio."""
    persona_id, bot_user_id = next(iter((v, k) for k, v in persona_id_by_bot_user_id().items()))
    persona = get_persona(persona_id)
    assert persona is not None

    loop = HostDispatchLoop(router=MagicMock(), mention_targets=persona_id_by_bot_user_id())
    message = SimpleNamespace(
        author=SimpleNamespace(id=int(bot_user_id), bot=True, display_name="apodo-del-guild"),
    )
    assert _client(loop)._context_author(message) == persona.display_name
    assert _client(loop)._context_author(message) != "apodo-del-guild"


def test_a_human_keeps_their_own_display_name():
    loop = HostDispatchLoop(router=MagicMock(), mention_targets=persona_id_by_bot_user_id())
    message = SimpleNamespace(author=SimpleNamespace(id=907264175246569543, bot=False, display_name="bernard2389"))
    assert _client(loop)._context_author(message) == "bernard2389"
