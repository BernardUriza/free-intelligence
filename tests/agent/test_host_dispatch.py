"""The host's route-and-dispatch core (#6, slice 2).

Positive: a batched turn is routed and the chosen persona is summoned via /invite
with the user's ask as the reason. Resistance: a router that raises never wedges
the host (returns None, no summon); a decision with no target summons nobody.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from demux_ai import dispatch


async def test_routes_and_summons_the_chosen_persona():
    router = SimpleNamespace(route=AsyncMock(return_value=SimpleNamespace(target="vultur", reason="llm_vultur")))
    with patch.object(dispatch, "summon_persona", new=AsyncMock(return_value=True)) as summon:
        decision = await dispatch.route_and_dispatch(
            router, channel_id="C1", text="reséñame Stalker", user_name="bernard"
        )
    assert decision.target == "vultur"
    summon.assert_awaited_once()
    kwargs = summon.await_args.kwargs
    assert kwargs["persona_id"] == "vultur"
    assert kwargs["invited_by"] == "host"
    assert "reséñame Stalker" in summon.await_args.args[0]["reason"]
    assert "bernard" in summon.await_args.args[0]["reason"]


async def test_trigger_message_id_reaches_the_summon_for_reactions():
    """The reaction anchor must ride through to /invite, else the routed turn's
    [REACT:] markers drop (the post-cutover regression this fixes)."""
    router = SimpleNamespace(route=AsyncMock(return_value=SimpleNamespace(target="frugivoro", reason="llm_frugivoro")))
    with patch.object(dispatch, "summon_persona", new=AsyncMock(return_value=True)) as summon:
        await dispatch.route_and_dispatch(router, channel_id="C1", text="receta vegana", trigger_message_id="m42")
    assert summon.await_args.kwargs["trigger_message_id"] == "m42"


async def test_router_exception_returns_none_and_summons_nobody():
    """RESISTANCE: a routing fault must never wedge the host or dispatch blind."""
    router = SimpleNamespace(route=AsyncMock(side_effect=RuntimeError("azure down")))
    with patch.object(dispatch, "summon_persona", new=AsyncMock()) as summon:
        result = await dispatch.route_and_dispatch(router, channel_id="C1", text="hola")
    assert result is None
    summon.assert_not_awaited()


async def test_no_target_summons_nobody():
    """RESISTANCE: a decision with an empty target is not dispatched."""
    router = SimpleNamespace(route=AsyncMock(return_value=SimpleNamespace(target="", reason="llm_unparseable")))
    with patch.object(dispatch, "summon_persona", new=AsyncMock()) as summon:
        result = await dispatch.route_and_dispatch(router, channel_id="C1", text="???")
    assert result is not None
    summon.assert_not_awaited()
