"""The door's half of the guard contract: what the wire may ask for, what it is
refused, and the shape of the `guards` event that comes back.

The wiring is OBSERVATIONAL by decision (2026-08-22): AIRE streams `text` events
as they arrive, so a guard that sees the finished text is looking at bytes the
caller already read. `text_override` and `retry` are therefore never applied —
but they ARE reported, because a safety net whose findings vanish is worse than
no net. These tests pin exactly that: nothing is silently swallowed."""

import json

import pytest
from fastapi import HTTPException

from aire.engine.contract import GuardOutcome
from aire.engine.guard_exec import observe
from aire.intake import safe_guards
from aire.messages import _guards_event


class Leaking:
    name = "leaking"

    def inspect(self, *, response_text, context=(), final=False):
        return GuardOutcome(metadata={"severity": "break", "matched": ["as an AI"]},
                            text_override="CLEAN", retry=True, reinforcement="stay in character")


class Quiet:
    name = "quiet"

    def inspect(self, *, response_text, context=(), final=False):
        return GuardOutcome()


def test_no_guards_field_costs_nothing():
    assert safe_guards(None) == [] and safe_guards([]) == []


def test_the_wire_cannot_define_a_guard_at_the_door():
    for hostile in ([{"command": "rm -rf /"}], ["nope"], "antidrift", [7]):
        with pytest.raises(HTTPException) as exc:
            safe_guards(hostile)
        assert exc.value.status_code == 422


def test_a_registered_guard_either_builds_or_says_503_never_silently_empty():
    # fi-core is not on PyPI, so the droplet's CI has no backing for `antidrift`.
    # Either outcome is correct; an empty list would NOT be — that is a request
    # accepted and quietly unserved.
    try:
        built = safe_guards(["antidrift"])
    except HTTPException as exc:
        assert exc.value.status_code == 503
    else:
        assert len(built) == 1 and built[0].name == "antidrift"


def test_an_override_is_reported_as_unenforced_never_applied():
    found = observe([Leaking()], "As an AI I cannot.", "dime algo")
    assert found["type"] == "guards"
    assert found["unenforced"] == ["leaking"]
    assert found["wanted_retry"] is True
    assert found["reinforcement"] == "stay in character"
    assert "CLEAN" not in json.dumps(found)


def test_a_clean_turn_reports_clean_and_asks_for_nothing():
    found = observe([Quiet()], "todo bien", "hola")
    assert found["unenforced"] == [] and found["wanted_retry"] is False
    assert found["findings"]["quiet"]["level"] == "ok"


def test_the_event_is_json_serializable_so_it_can_reach_the_wire():
    ev = _guards_event([Leaking()], {"result": type("R", (), {"text": "As an AI"})()}, "hola")
    assert ev.event == "guards"
    body = json.loads(ev.data)
    assert body["findings"]["leaking"]["matched"] == ["as an AI"]


def test_a_result_without_text_does_not_crash_the_stream():
    ev = _guards_event([Quiet()], {"result": None}, "hola")
    assert json.loads(ev.data)["findings"]["quiet"]["level"] == "ok"
