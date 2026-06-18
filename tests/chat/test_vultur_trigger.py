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


# --- HOST 5/6 slice A: shadow router (behavior-neutral + logged) -------------

from structlog.testing import capture_logs  # noqa: E402

from demux_ai.shadow_router import shadow_route  # noqa: E402


def _make_ctx_shadow(text: str, *, route=shadow_route) -> TurnCtx:
    ctx = _make_ctx(text)
    ctx.deps.shadow_route = route
    return ctx


@pytest.mark.asyncio
async def test_shadow_logs_decision_for_normal_message():
    ctx = _make_ctx_shadow("oye insult qué onda")
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    # behavior-neutral: live routing untouched
    assert ctx.persona_id is None
    assert ctx.text == "oye insult qué onda"
    sd = [e for e in logs if e["event"] == "shadow_router_decision"]
    assert len(sd) == 1
    assert sd[0]["current_target"] == "insult"
    assert sd[0]["shadow_target"] == "insult"
    assert sd[0]["diverged"] is False


@pytest.mark.asyncio
async def test_shadow_mirrors_live_vultur_no_divergence():
    # Shadow sees the RAW (pre-strip) text, so it observes the @vultur prefix the
    # same way the live rule did → shadow_target=vultur, diverged=False.
    ctx = _make_ctx_shadow("@vultur reseña Hereditary")
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    assert ctx.persona_id == "vultur"
    assert ctx.text == "reseña Hereditary"
    sd = next(e for e in logs if e["event"] == "shadow_router_decision")
    assert sd["current_target"] == "vultur"
    assert sd["shadow_target"] == "vultur"
    assert sd["diverged"] is False


@pytest.mark.asyncio
async def test_shadow_disabled_emits_no_decision():
    ctx = _make_ctx_shadow("hola", route=None)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    assert not [e for e in logs if e["event"] == "shadow_router_decision"]


@pytest.mark.asyncio
async def test_shadow_fault_is_invisible_to_turn():
    def _boom(_text):
        raise RuntimeError("shadow exploded")

    ctx = _make_ctx_shadow("@vultur dame cine", route=_boom)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    # the turn is unaffected by a shadow fault
    assert ctx.persona_id == "vultur"
    assert ctx.text == "dame cine"
    assert any(e["event"] == "shadow_router_failed" for e in logs)
    assert not [e for e in logs if e["event"] == "shadow_router_decision"]
