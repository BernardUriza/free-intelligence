"""The guard registry's security contract and the executor's failure algebra.

Two things are pinned here. First, the wire may NAME a guard and never DEFINE
one — the daemon is internet-open and runs as root, so a caller-supplied pattern
would be a ReDoS handed to a stranger. Second, a guard is a safety NET, never a
single point of failure: one that raises is logged and skipped while its
siblings' findings still land."""

import pytest

from aire.engine.contract import Guard, GuardOutcome
from aire.engine.guard_exec import guard_level, run_guards
from aire.engine.guard_registry import REGISTRY, UnknownGuard, clean_guards


class Sanitizing:
    name = "sanitizing"

    def inspect(self, *, response_text, context=(), final=False):
        return GuardOutcome(metadata={"severity": "break", "critical": True},
                            text_override="CLEAN", retry=True, reinforcement="stay in character")


class Raising:
    name = "raising"

    def inspect(self, **kw):
        raise ValueError("bad pattern")


class Clean:
    name = "clean"

    def inspect(self, *, response_text, context=(), final=False):
        return GuardOutcome()


def collect():
    events: list[str] = []
    return events, lambda e, f: events.append(e)


def test_the_wire_cannot_define_a_guard_only_name_one():
    for hostile in ([{"command": "rm -rf /"}], ["antidrift", {"x": 1}], [42], "antidrift"):
        with pytest.raises(UnknownGuard):
            clean_guards(hostile)


def test_an_unknown_name_is_refused_and_says_what_exists():
    with pytest.raises(UnknownGuard) as exc:
        clean_guards(["pwn"])
    assert "pwn" in str(exc.value) and "antidrift" in str(exc.value)


def test_known_names_are_deduped_in_order():
    assert clean_guards(["antidrift", "antidrift"]) == ["antidrift"]


def test_no_guards_requested_is_not_an_error():
    assert clean_guards(None) == [] and clean_guards([]) == []


def test_every_registered_name_maps_to_a_callable_factory():
    # Deliberately does NOT build them: a factory imports its fi-core backing,
    # and fi-core is not on PyPI, so CI on the droplet's requirements has none.
    for name, factory in REGISTRY.items():
        assert callable(factory), name


def test_a_guard_that_raises_is_logged_and_skipped_not_fatal():
    events, emit = collect()
    text, outcomes, retry, _ = run_guards([Raising(), Clean()], "original", "hi",
                                          final=False, emit=emit)
    assert text == "original"
    assert outcomes["raising"].metadata["guard_failed"] is True
    assert outcomes["clean"].clean
    assert "guard_error" in events


def test_a_broken_guard_does_not_cancel_its_siblings_sanitize():
    events, emit = collect()
    text, _, retry, reinforcement = run_guards([Raising(), Sanitizing()], "leaked", "hi",
                                               final=False, emit=emit)
    assert text == "CLEAN"
    assert retry is True and reinforcement == "stay in character"


def test_a_critical_finding_surfaces_as_telemetry():
    events, emit = collect()
    run_guards([Sanitizing()], "leaked", "hi", final=False, emit=emit)
    assert "guard_critical" in events


def test_overrides_apply_in_order_so_a_later_guard_sees_clean_text():
    class Second:
        name = "second"

        def inspect(self, *, response_text, context=(), final=False):
            return GuardOutcome(metadata={"saw": response_text})

    _, outcomes, _, _ = run_guards([Sanitizing(), Second()], "leaked", "hi",
                                   final=False, emit=lambda e, f: None)
    assert outcomes["second"].metadata["saw"] == "CLEAN"


def test_a_clean_outcome_asks_for_nothing():
    o = GuardOutcome()
    assert o.clean and not o.retry and o.text_override is None


def test_guard_level_reads_error_before_anything_else():
    assert guard_level({"guard_failed": True, "level": "CRITICAL"}) == "error"
    assert guard_level({"level": "CRITICAL"}) == "CRITICAL"
    assert guard_level({"severity": "soft_drift"}) == "soft_drift"
    assert guard_level({}) == "ok"


def test_the_fakes_satisfy_the_published_protocol():
    assert isinstance(Sanitizing(), Guard) and isinstance(Clean(), Guard)
