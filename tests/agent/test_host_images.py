"""Imágenes pelonas rutean — el host deja de ser ciego a adjuntos.

El bug (2026-07-16, msg 1527449724779626607): una imagen sin texto era
text="" → el batcher la tiraba en pop_due y NADIE respondía jamás; y en un
burst imagen+texto el trigger era el mensaje de texto, así que el invite path
fetcheaba un mensaje sin adjuntos y la imagen se perdía igual.

Mutator rule: positivos (imagen pelona rutea con nota visible; el trigger del
burst prefiere el mensaje con adjuntos) + resistencia (sin adjuntos nada
cambia: trigger = último mensaje con texto real; comandos con adjunto se
siguen ignorando).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from demux_ai import dispatch
from demux_ai.batch import MessageBatcher
from demux_ai.host_loop import HostDispatchLoop


def _loop(target="insult") -> HostDispatchLoop:
    router = SimpleNamespace(route=AsyncMock(return_value=SimpleNamespace(target=target, reason=f"llm_{target}")))
    return HostDispatchLoop(router=router, batcher=MessageBatcher(window_seconds=3.0))


async def test_bare_image_routes_with_visible_note():
    """Una imagen SIN texto se batchea como nota routable y despacha con el
    mensaje de la imagen como trigger."""
    loop = _loop()
    assert loop.handle_message(
        channel_id="C1",
        author_id="u1",
        author_is_bot=False,
        text="",
        now=100.0,
        author_name="bern",
        message_id="IMG-1",
        attachment_names=["foto.png"],
    )
    with patch.object(dispatch, "summon_persona", new=AsyncMock(return_value=True)) as summon:
        decisions = await loop.tick(now=104.0)
    assert [d.target for d in decisions] == ["insult"]
    assert "[adjuntó: foto.png]" in summon.await_args.args[0]["reason"]
    assert summon.await_args.kwargs["trigger_message_id"] == "IMG-1"


async def test_image_then_text_burst_prefers_the_image_as_trigger():
    """Burst imagen→texto: el texto entra al reason pero el trigger es el
    mensaje CON la imagen — el invite path cosecha adjuntos del trigger."""
    loop = _loop()
    loop.handle_message(
        channel_id="C1",
        author_id="u1",
        author_is_bot=False,
        text="",
        now=100.0,
        message_id="IMG-1",
        attachment_names=["tacos.jpg"],
    )
    loop.handle_message(
        channel_id="C1", author_id="u1", author_is_bot=False, text="que ricoooo", now=101.0, message_id="TXT-2"
    )
    with patch.object(dispatch, "summon_persona", new=AsyncMock(return_value=True)) as summon:
        decisions = await loop.tick(now=105.0)
    assert len(decisions) == 1
    reason = summon.await_args.args[0]["reason"]
    assert "que ricoooo" in reason
    assert "[adjuntó: tacos.jpg]" in reason
    assert summon.await_args.kwargs["trigger_message_id"] == "IMG-1"


async def test_text_only_burst_keeps_last_text_message_as_trigger():
    """RESISTENCIA: sin adjuntos el comportamiento no cambia — el anchor es el
    último mensaje con texto real."""
    loop = _loop()
    loop.handle_message(channel_id="C1", author_id="u1", author_is_bot=False, text="oye", now=100.0, message_id="M1")
    loop.handle_message(
        channel_id="C1", author_id="u1", author_is_bot=False, text="una duda", now=101.0, message_id="M2"
    )
    with patch.object(dispatch, "summon_persona", new=AsyncMock(return_value=True)) as summon:
        await loop.tick(now=105.0)
    assert summon.await_args.kwargs["trigger_message_id"] == "M2"


async def test_command_with_attachment_stays_ignored():
    """RESISTENCIA: un !comando con adjunto sigue siendo comando — no rutea."""
    loop = _loop()
    assert not loop.handle_message(
        channel_id="C1",
        author_id="u1",
        author_is_bot=False,
        text="!chat mira",
        now=100.0,
        message_id="CMD-1",
        attachment_names=["x.png"],
    )
    with patch.object(dispatch, "summon_persona", new=AsyncMock(return_value=True)):
        assert await loop.tick(now=105.0) == []
