"""Stage-01 Vultur trigger: @vultur / ~vultur prefix → persona_id routing.

Four required cases (coagent spec):
1. @vultur <text> → persona_id="vultur", text stripped
2. ~vultur <text> → persona_id="vultur", text stripped
3. normal message  → persona_id=None (Insult default)
4. bare trigger (no text after prefix) → persona_id="vultur", text=""

Mutator rules: positive + resistance (normal messages untouched).
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from personas.insult.cogs.chat.pipeline import TurnCtx
from personas.insult.cogs.chat.stages import _stage_bind_identity


def _make_ctx(text: str) -> TurnCtx:
    msg = MagicMock()
    msg.channel.id = 111
    msg.author.id = 222
    msg.author.display_name = "tester"
    msg.guild = None
    msg.channel.name = "general"
    msg.attachments = []
    msg.flags.voice = False
    return TurnCtx(message=msg, text=text, turn_start=time.monotonic(), deps=MagicMock())


@pytest.mark.asyncio
async def test_at_vultur_sets_persona_id():
    ctx = _make_ctx("@vultur reseña Hereditary")
    await _stage_bind_identity(ctx)
    assert ctx.persona_id == "vultur"
    assert ctx.text == "reseña Hereditary"


@pytest.mark.asyncio
async def test_tilde_vultur_sets_persona_id():
    ctx = _make_ctx("~vultur ¿qué piensas de Midsommar?")
    await _stage_bind_identity(ctx)
    assert ctx.persona_id == "vultur"
    assert ctx.text == "¿qué piensas de Midsommar?"


@pytest.mark.asyncio
async def test_normal_message_keeps_insult_default():
    ctx = _make_ctx("oye insult qué onda")
    await _stage_bind_identity(ctx)
    assert ctx.persona_id is None
    assert ctx.text == "oye insult qué onda"


@pytest.mark.asyncio
async def test_bare_trigger_no_text():
    ctx = _make_ctx("@vultur ")
    await _stage_bind_identity(ctx)
    assert ctx.persona_id == "vultur"
    assert ctx.text == ""
