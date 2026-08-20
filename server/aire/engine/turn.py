"""One turn's lifecycle: query, drain, and the two lying-green detections at
the result seam — the budget cut (#23) and the burned credential pool (#31).
The Engine facade delegates here so `core.py` stays inside the 150-line law.

A burned attempt never yields its lying result: the slot cools, the poisoned
client is retired, and the turn retries on the next slot — each slot gets at
most ONE attempt per turn. All slots dry → a real `credentials_exhausted`
error. Red stays red."""

from collections.abc import AsyncIterator
from typing import Any

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


async def _attempt(engine: Any, project: str, session: str, prompt: str,
                   spec: TurnSpec, images: tuple[dict[str, str], ...],
                   slot: Any) -> AsyncIterator[dict[str, Any]]:
    key = f"{project}/{session}"
    client, lock = await engine._client_for(project, session, spec, slot)
    born_with = engine.slot_of.get(key, slot.name)
    spent = burned = False
    try:
        async with lock:
            await send_turn(client, prompt, images)
            async for event in drain(client):
                if event.get("type") == "result":
                    spent = engine._account(key, turn_cost(event))
                    result = event["result"]
                    if limit_hit(result.text, result.usage):
                        burned = True
                        continue
                yield event
            if spent:
                yield engine._budget_cut_event()
    finally:
        if spent or burned:
            await engine._retire(project, session)
    if burned:
        engine.rotor.burn(born_with)
        yield _ROTATE
