"""PR-4b slice 3 — gpt-4.1 host degrader, wired INERT.

Slice 3 adds the gpt-4.1 host degrader to the honest-degradation tail of a
fully-failed turn, behind ``host_router_enabled`` (default False). This pins:

- The degrader (demux side) returns a stripped notice on success and re-raises
  ``HostRouterError`` on a host-router failure — it never swallows its own
  failure into a fake-green string.
- INERT default (``host_degrader=None``): the honest-degradation tail delivers
  the STATIC in-character notice exactly as before — gpt-4.1 is never consulted.
  This is the resistance case guarding the "no prod change" promise.
- Enabled + degrader succeeds: its authored notice is delivered instead.
- Enabled + degrader raises ``HostRouterError``: the turn falls back
  CONSERVATIVELY to the static notice (never silent, never the raised error),
  and the failure is the ``ROUTER_ERROR`` path.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

import personas.insult.cogs.chat.stages as stages
from demux_ai.host_degrader import HostDegrader
from demux_ai.host_llm import HostLLMResult, HostRouterError
from khimeras_shared.runner.agent_client import PersonaTurnError
from personas.insult.cogs.chat._failure import StageFailure
from personas.insult.cogs.chat.pipeline import TurnCtx, TurnRuntimeDeps

# --------------------------------------------------------------------------
# Degrader unit (demux side) — success returns text, failure re-raises
# --------------------------------------------------------------------------


class TestHostDegrader:
    @pytest.mark.asyncio
    async def test_degrade_returns_stripped_router_text(self):
        router = MagicMock()
        router.complete = AsyncMock(
            return_value=HostLLMResult(
                text="  Ahora no puedo atender, inténtalo en un momento.  ",
                model="gpt-4.1",
                input_tokens=10,
                output_tokens=8,
                latency_ms=120,
            )
        )
        degrader = HostDegrader(router=router)

        out = await degrader.degrade(reason="runner_down", user_text="oye")

        assert out == "Ahora no puedo atender, inténtalo en un momento."
        router.complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_degrade_reraises_host_router_error(self):
        """A host-router failure is NOT swallowed — it surfaces as
        HostRouterError so the caller can take the conservative fallback."""
        router = MagicMock()
        router.complete = AsyncMock(side_effect=HostRouterError("gpt-4.1 down"))
        degrader = HostDegrader(router=router)

        with pytest.raises(HostRouterError):
            await degrader.degrade(reason="runner_down", user_text="oye")


# --------------------------------------------------------------------------
# Stages integration — honest-degradation tail consumes the degrader port
# --------------------------------------------------------------------------


def _mk_llm_ctx(*, host_degrader=None) -> TurnCtx:
    """A turn whose primary backend raises PersonaTurnError (a LIVE runner
    rejecting THIS turn) → no ALICE failover, straight to honest degradation."""
    settings = MagicMock()
    settings.alice_failover_enabled = True
    settings.llm_model = "claude"

    channel = MagicMock()
    channel.id = 42
    channel.send = AsyncMock(return_value=None)
    message = MagicMock()
    message.channel = channel
    message.add_reaction = AsyncMock(return_value=None)

    agent_client = MagicMock()
    agent_client.chat = AsyncMock(side_effect=PersonaTurnError("runner 422"))

    ctx = TurnCtx(
        message=message,
        text="oye",
        turn_start=time.monotonic(),
        deps=TurnRuntimeDeps(
            memory=MagicMock(),
            settings=settings,
            bot=MagicMock(),
            expression_history=MagicMock(),
            opus_budget=MagicMock(),
            spawn_task=lambda *a, **kw: None,
            all_tools=[],
            facts=MagicMock(),
            stance=MagicMock(),
            arc=MagicMock(),
            retrieval=MagicMock(),
            preset_engine=MagicMock(),
            policy=MagicMock(),
            mutation=MagicMock(),
            agent_client=agent_client,
            host_degrader=host_degrader,
        ),
    )
    ctx.channel_id = "42"
    ctx.user_id = "7"
    ctx.guild_id = "99"
    ctx.channel_name = "general"
    ctx.system_prompt = "sys"
    ctx.context = []
    ctx.tools = []
    ctx.tool_choice = None
    ctx.model_choice = None
    ctx.persona_id = None
    return ctx


@pytest.fixture(autouse=True)
def _stub_pre_chat(monkeypatch):
    monkeypatch.setattr(stages, "_build_behavioral_guidance", lambda ctx: "")

    async def _empty_knowledge(*a, **k):
        return MagicMock(combined_memory=None, other_people_block=None)

    monkeypatch.setattr(stages, "assemble_knowledge", _empty_knowledge)


# get_error_response picks a RANDOM in-character variant, so pin it to a
# deterministic sentinel — the static notice's CONTENT is owned by core.errors
# and tested there; here we only assert WHICH path (static vs degrader) ran.
_STATIC = "<static-in-character-notice>"


@pytest.fixture(autouse=True)
def _deterministic_static_notice(monkeypatch):
    monkeypatch.setattr(stages, "get_error_response", lambda _err: _STATIC)


@pytest.mark.asyncio
async def test_inert_default_delivers_static_notice():
    """host_degrader=None (prod default) → static in-character notice, gpt-4.1
    never consulted. The 'no prod change' resistance case."""
    ctx = _mk_llm_ctx(host_degrader=None)

    with pytest.raises(StageFailure):
        await stages._stage_call_llm(ctx)

    ctx.message.channel.send.assert_awaited_once_with(_STATIC)


@pytest.mark.asyncio
async def test_enabled_degrader_authors_the_notice():
    """host_degrader present + succeeds → its authored notice is delivered."""
    degrader = MagicMock()
    degrader.degrade = AsyncMock(return_value="Ahora no se puede, vuelve en un momento.")
    ctx = _mk_llm_ctx(host_degrader=degrader)

    with pytest.raises(StageFailure):
        await stages._stage_call_llm(ctx)

    degrader.degrade.assert_awaited_once_with(reason="persona_error", user_text="oye")
    ctx.message.channel.send.assert_awaited_once_with("Ahora no se puede, vuelve en un momento.")


@pytest.mark.asyncio
async def test_enabled_degrader_blank_result_falls_back_to_static():
    """host_degrader returns a blank/whitespace notice (NOT an exception) →
    keep the static notice, never send "" to Discord. Resistance case for the
    conservative-fallback completeness guard."""
    degrader = MagicMock()
    degrader.degrade = AsyncMock(return_value="   \n  ")
    ctx = _mk_llm_ctx(host_degrader=degrader)

    with pytest.raises(StageFailure):
        await stages._stage_call_llm(ctx)

    degrader.degrade.assert_awaited_once()
    ctx.message.channel.send.assert_awaited_once_with(_STATIC)


@pytest.mark.asyncio
async def test_enabled_degrader_router_error_falls_back_to_static():
    """host_degrader raises HostRouterError (ROUTER_ERROR) → conservative
    fallback to the static notice, never silent, never the raised error."""
    degrader = MagicMock()
    degrader.degrade = AsyncMock(side_effect=HostRouterError("gpt-4.1 down"))
    ctx = _mk_llm_ctx(host_degrader=degrader)

    with pytest.raises(StageFailure):
        await stages._stage_call_llm(ctx)

    degrader.degrade.assert_awaited_once()
    ctx.message.channel.send.assert_awaited_once_with(_STATIC)
