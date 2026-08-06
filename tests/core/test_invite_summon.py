"""`[INVITE:]` summons the sibling again — and strips no matter what.

The marker's summon died with `personas/` on 2026-07-14 and was not rebuilt, so
for three weeks Insult could emit `[INVITE:]` and nothing happened. Worse, with
no stripper either, on 2026-07-31 the raw note reached Bernard.

The gateway runs every persona in ONE process, so the summon is a direct call to
the sibling's guarded `dispatch_invite` — no HTTP hop, no second token. These
pin both halves: the sibling gets called, and the marker never survives.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from persona_gateway.markers import INVITE_PERSONA_ID, MarkerRouter


def _router(persona_id: str = "insult") -> MarkerRouter:
    persona = SimpleNamespace(persona_id=persona_id)
    return MarkerRouter(persona, memory=SimpleNamespace())


def _sibling(*, ready: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        user=object() if ready else None,
        dispatch_invite=AsyncMock(return_value=None),
    )


async def _drain(router: MarkerRouter) -> None:
    """Let the fire-and-forget summon task actually run."""
    await asyncio.gather(*list(router._bg_tasks), return_exceptions=True)


class TestSummon:
    @pytest.mark.asyncio
    async def test_the_sibling_is_summoned_with_the_reason(self):
        router = _router()
        alice = _sibling()
        router.bind_siblings({INVITE_PERSONA_ID: alice})

        out = await router._route_invite(
            "sostengo yo [INVITE: entra suave, está en crisis]",
            channel_id="C1",
            guild_id="G1",
            user_id="U1",
        )
        await _drain(router)

        alice.dispatch_invite.assert_awaited_once()
        kwargs = alice.dispatch_invite.await_args.kwargs
        assert kwargs["reason"] == "entra suave, está en crisis"
        assert kwargs["channel_id"] == "C1"
        assert kwargs["guild_id"] == "G1"
        assert kwargs["invited_by"] == "insult"
        assert out == "sostengo yo"

    @pytest.mark.asyncio
    async def test_a_turn_without_the_marker_summons_nobody(self):
        """RESISTANCE: most turns don't need her. The DNA says once every 10-20
        turns — a router that summoned on every turn would make Insult her usher."""
        router = _router()
        alice = _sibling()
        router.bind_siblings({INVITE_PERSONA_ID: alice})

        out = await router._route_invite("un turno normal", channel_id="C1", guild_id=None, user_id="U1")

        alice.dispatch_invite.assert_not_awaited()
        assert out == "un turno normal"


class TestStripSurvivesEveryFailure:
    """The marker reaching a human is the failure with a real victim, so every
    branch that can go wrong must still strip."""

    @pytest.mark.asyncio
    async def test_stripped_when_no_siblings_are_bound(self):
        router = _router()  # bind_siblings never called — the pre-fix prod state

        out = await router._route_invite("texto [INVITE: ven]", channel_id="C1", guild_id=None, user_id="U1")

        assert out == "texto"

    @pytest.mark.asyncio
    async def test_stripped_when_the_sibling_is_still_booting(self):
        router = _router()
        router.bind_siblings({INVITE_PERSONA_ID: _sibling(ready=False)})

        out = await router._route_invite("texto [INVITE: ven]", channel_id="C1", guild_id=None, user_id="U1")

        assert out == "texto"

    @pytest.mark.asyncio
    async def test_a_persona_never_summons_itself(self):
        """RESISTANCE: ALICE emitting the marker must not invite ALICE — that is
        an invite loop with a real Discord message on every lap."""
        router = _router(persona_id=INVITE_PERSONA_ID)
        alice = _sibling()
        router.bind_siblings({INVITE_PERSONA_ID: alice})

        out = await router._route_invite("texto [INVITE: yo misma]", channel_id="C1", guild_id=None, user_id="U1")

        alice.dispatch_invite.assert_not_awaited()
        assert out == "texto"
