"""One turn's lifecycle: query, drain, and the two lying-green detections at
the result seam — the budget cut (#23) and the burned credential pool (#31).
The Engine facade delegates here so `core.py` stays inside the 150-line law.

A burned attempt never yields its lying result: the slot cools, the poisoned
client is retired, and the turn retries on the next slot — each slot gets at
most ONE attempt per turn. All slots dry → a real `credentials_exhausted`
error. Red stays red."""

from collections.abc import AsyncIterator
from typing import Any

from .. import spend
from .contract import BudgetExceeded, TurnSpec
from .credentials import is_metered, limit_hit
from .drain import drain, turn_cost, turn_tokens
from .vision import send_turn

_ROTATE: dict[str, Any] = {"type": "_rotate"}


def _all_dry_event(rotor: Any) -> dict[str, Any]:
    return {"type": "error", "error": "credentials_exhausted",
            "detail": "every credential slot is cooling after a usage-limit hit; "
                      f"next probe in {rotor.retry_after_s()}s",
            "cooling": rotor.cooling_names()}


async def run_turn(engine: Any, project: str, session: str, prompt: str,
                   spec: TurnSpec,
                   images: tuple[dict[str, str], ...] = ()) -> AsyncIterator[dict[str, Any]]:
    """Walk the credential chain until an attempt survives or the chain dries.
    Terminates: every rotation cools one more slot, and `active()` skips them."""
    while True:
        slot = engine.rotor.active()
        if slot is None:
            yield _all_dry_event(engine.rotor)
            return
        # The spend ceiling guards the CARD, so it refuses only turns that would
        # ride a metered slot. A subscription turn costs nothing real; blocking
        # it here is how every persona went mute for 16 hours on 2026-08-25.
        if is_metered(slot.name) and engine.ledger.exhausted():
            raise BudgetExceeded(engine.ledger.refusal())
        rotated = False
        async for event in _attempt(engine, project, session, prompt, spec, images, slot):
            if event is _ROTATE:
                rotated = True
            else:
                yield event
        if not rotated:
            return


async def _account(engine: Any, project: str, session: str,
                   event: dict[str, Any], slot_name: str) -> bool:
    """Bank this turn twice, for two different questions, and report whether the
    client hit its own cap (#23).

    In RAM the ``Ledger`` answers "should this process stop lending the CARD" —
    so only a metered slot's dollars move it (``is_metered``); in Postgres
    ``aire_spend`` answers "what did AIRE spend this month" and records every
    turn, nominal or not — the one the RAM counter can never answer, because it
    is born at zero on every deploy.

    The dollars are the DELTA, never ``total_cost_usd``, which is the client's
    CUMULATIVE spend: banking it whole would bill the same money once per turn.
    The slot is the one the client was BORN with, not this attempt's — the
    client that spent is the one that pays."""
    metered = is_metered(slot_name)
    delta, spent = engine.ledger.account(f"{project}/{session}", turn_cost(event), metered)
    await spend.bank("engine", project, session, None, delta, metered, turn_tokens(event))
    return spent


async def _attempt(engine: Any, project: str, session: str, prompt: str,
                   spec: TurnSpec, images: tuple[dict[str, str], ...],
                   slot: Any) -> AsyncIterator[dict[str, Any]]:
    key = f"{project}/{session}"
    # A pooled client binds mode/tools/model at birth; a turn that asks for a
    # different shape must not be answered by the old one in silence (#38).
    await engine._rebind(project, session, spec)
    client, lock = await engine._client_for(project, session, spec, slot)
    born_with = engine.slot_of.get(key, slot.name)
    spent = False
    notice: str | None = None
    try:
        async with lock:
            await send_turn(client, prompt, images)
            async for event in drain(client):
                if event.get("type") == "result":
                    spent = await _account(engine, project, session, event, born_with)
                    result = event["result"]
                    if limit_hit(result.text, result.usage):
                        notice = result.text
                        continue
                yield event
            if spent:
                yield engine.ledger.cut_event()
    finally:
        if spent or notice is not None:
            await engine._retire(project, session)
    if notice is not None:
        engine.rotor.burn(born_with, notice)
        yield _ROTATE
