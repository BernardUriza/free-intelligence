"""DASH-1c (v3.9.45): ops-signal counters in metrics.

Pins the wire between structlog events and the dashboard metrics blob.
If a counter goes missing or the event name on the producer side drifts,
the dashboard silently stops counting — only this test catches that.
"""

from __future__ import annotations

import pytest

from personas.insult.core import metrics


@pytest.fixture(autouse=True)
def _reset_counters():
    """Snapshot + restore the global counters so tests don't bleed into each other."""
    snapshot = dict(metrics._counters)
    yield
    metrics._counters.clear()
    metrics._counters.update(snapshot)


def test_zombie_restart_increments_counter():
    before = metrics._counters["gateway_zombie_restarts"]
    metrics.record_event({"event": "gateway_watchdog_zombie_detected_restart"})
    assert metrics._counters["gateway_zombie_restarts"] == before + 1


def test_heartbeat_dead_restart_increments_counter():
    before = metrics._counters["gateway_heartbeat_dead_restarts"]
    metrics.record_event({"event": "gateway_watchdog_heartbeat_dead_restart"})
    assert metrics._counters["gateway_heartbeat_dead_restarts"] == before + 1


def test_alice_failover_increments_counter():
    before = metrics._counters["alice_failovers"]
    metrics.record_event({"event": "alice_failover_invoked"})
    assert metrics._counters["alice_failovers"] == before + 1


def test_invoke_alice_increments_counter():
    before = metrics._counters["invoke_alice_calls"]
    metrics.record_event({"event": "invoke_alice_called"})
    assert metrics._counters["invoke_alice_calls"] == before + 1


def test_remember_fact_increments_counter():
    before = metrics._counters["remember_facts_added"]
    metrics.record_event({"event": "remember_fact_added"})
    assert metrics._counters["remember_facts_added"] == before + 1


def test_image_turn_increments_counter():
    before = metrics._counters["agent_runner_image_turns"]
    metrics.record_event({"event": "agent_runner_client_attachments_forwarded"})
    assert metrics._counters["agent_runner_image_turns"] == before + 1


def test_unrelated_event_does_not_touch_ops_counters():
    """A common event shouldn't bump any of the new ops counters.

    Asserts each counter is UNCHANGED across one health_check event, not
    equal to zero. The original `== 0` form was flaky under non-default
    test order: when another module-level test ran first it bumped a
    counter, the autouse `_reset_counters` snapshot captured the bumped
    value (not zero), and this test then failed at assertion time. Same
    intent ("unrelated event must not touch these counters"), correctly
    expressed as a delta against the pre-event snapshot."""
    keys = (
        "gateway_zombie_restarts",
        "gateway_heartbeat_dead_restarts",
        "alice_failovers",
        "invoke_alice_calls",
        "remember_facts_added",
        "agent_runner_image_turns",
    )
    before = {k: metrics._counters[k] for k in keys}
    metrics.record_event({"event": "health_check"})
    for k in keys:
        assert metrics._counters[k] == before[k], f"{k} bumped by health_check"


def test_metrics_snapshot_includes_ops_counters():
    """The blob the dashboard fetches must include every ops counter."""
    snapshot = metrics.build_metrics_snapshot(bot_latency_ms=20, guilds=1, db_stats={})
    counters = snapshot.get("counters", {})
    for k in (
        "gateway_zombie_restarts",
        "gateway_heartbeat_dead_restarts",
        "alice_failovers",
        "invoke_alice_calls",
        "remember_facts_added",
        "agent_runner_image_turns",
    ):
        assert k in counters, f"{k} missing from metrics snapshot"


# --- preset_classified: one turn, one count ---------------------------------
#
# The event had TWO emitters (chat stage 08 with `preset=`, the prompt layer with
# `mode=`). Both bumped messages_total; only the `mode=` one matched a per-preset
# key. So `preset_X / messages_total` read HALF its true value and the documented
# "flag if 90%+ of classifications are DEFAULT_ABRASIVE" drift alarm could not
# trip at any real drift level. Prod: 418 events for 219 turns.


def test_one_classified_turn_counts_one_message():
    before = metrics._counters["messages_total"]
    metrics.record_event({"event": "preset_classified", "preset": "default_abrasive"})
    assert metrics._counters["messages_total"] == before + 1


def test_classified_turn_increments_its_preset_key():
    before = metrics._counters["preset_playful_roast"]
    metrics.record_event({"event": "preset_classified", "preset": "playful_roast"})
    assert metrics._counters["preset_playful_roast"] == before + 1


def test_the_drift_ratio_is_readable_from_the_counters():
    """RESISTANCE: with the double emitter this ratio came out at 0.5 for a
    channel that was 100% abrasive — the alarm's threshold was unreachable."""
    metrics._counters["messages_total"] = 0
    metrics._counters["preset_default_abrasive"] = 0
    for _ in range(10):
        metrics.record_event({"event": "preset_classified", "preset": "default_abrasive"})
    ratio = metrics._counters["preset_default_abrasive"] / metrics._counters["messages_total"]
    assert ratio == 1.0, f"a fully abrasive channel must read 100%, read {ratio:.0%}"
