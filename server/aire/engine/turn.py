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
from .contract import TurnSpec
from .credentials import limit_hit
from .drain import drain, turn_cost
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
        rotated = False
        async for event in _attempt(engine, project, session, prompt, spec, images, slot):
            if event is _ROTATE:
                rotated = True
            else:
                yield event
        if not rotated:
            return


async def _account(engine: Any, project: str, session: str,
                   event: dict[str, Any]) -> bool:
    """Bank this turn twice, for two different questions, and report whether the
    client hit its own cap (#23).

    In RAM the ``Ledger`` answers "should this process stop"; in Postgres
    ``aire_spend`` answers "what did AIRE spend this month" — the one the RAM
    counter can never answer, because it is born at zero on every deploy.

    The dollars are the DELTA, never ``total_cost_usd``, which is the client's
    CUMULATIVE spend: the ledger's own counter moves by exactly that delta, so
    reading it across the call bills the same money once."""
    before = engine.ledger.spend_usd
    spent = engine.ledger.account(f"{project}/{session}", turn_cost(event))
    await spend.bank("engine", project, session, None,
                     engine.ledger.spend_usd - before)
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
    spent = burned = False
    try:
        async with lock:
            await send_turn(client, prompt, images)
            async for event in drain(client):
                if event.get("type") == "result":
                    spent = await _account(engine, project, session, event)
                    result = event["result"]
                    if limit_hit(result.text, result.usage):
                        burned = True
                        continue
                yield event
            if spent:
                yield engine.ledger.cut_event()
    finally:
        if spent or burned:
            await engine._retire(project, session)
    if burned:
        engine.rotor.burn(born_with)
        yield _ROTATE
