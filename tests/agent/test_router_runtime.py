"""Unit coverage for runner session routing runtime."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from persona_runner.routing import router_runtime


@pytest.fixture(autouse=True)
def _fresh_opus_budget():
    """Each test starts with an empty in-memory Opus budget."""
    old_budget = router_runtime._reset_budget_for_tests()
    try:
        yield
    finally:
        router_runtime._BUDGET = old_budget


async def test_disclosure_severity_returns_row_value():
    """Disclosure severity returns the integer selected by asyncpg."""
    conn = AsyncMock()
    conn.fetchrow.return_value = {"s": 2}

    severity = await router_runtime._disclosure_severity(conn, "user-1")

    assert severity == 2
    conn.fetchrow.assert_awaited_once_with(
        "SELECT COALESCE(MAX(severity), 0)::int AS s FROM disclosure_log WHERE user_id = $1",
        "user-1",
    )


async def test_disclosure_severity_defaults_to_zero_without_rows():
    """Resistance: no disclosure row defaults to severity zero."""
    conn = AsyncMock()
    conn.fetchrow.return_value = None

    severity = await router_runtime._disclosure_severity(conn, "user-1")

    assert severity == 0


async def test_route_for_session_without_pg_conn_still_routes_from_text():
    """Missing asyncpg connection does not prevent text-only routing."""
    decision = await router_runtime.route_for_session(
        channel_id="channel-1",
        user_id="user-1",
        user_text="hola que tal",
        pg_conn=None,
    )

    assert decision.model == router_runtime.CASUAL_MODEL
    assert decision.tier == "casual"
    assert decision.reason == "casual_preset"
    assert decision.preset_mode == "default_abrasive"
    assert decision.disclosure_severity == 0
    assert decision.forced is False


async def test_route_for_session_survives_disclosure_query_failure():
    """Disclosure query failures fall back to severity zero and still route."""
    conn = AsyncMock()
    conn.fetchrow.side_effect = Exception("postgres unavailable")

    decision = await router_runtime.route_for_session(
        channel_id="channel-1",
        user_id="user-1",
        user_text="hola que tal",
        pg_conn=conn,
    )

    assert decision.model == router_runtime.CASUAL_MODEL
    assert decision.tier == "casual"
    assert decision.reason == "casual_preset"
    assert decision.disclosure_severity == 0
    conn.fetchrow.assert_awaited_once()


async def test_route_for_session_escalates_serious_preset_to_crisis():
    """A real serious preset classification escalates the session to Opus."""
    decision = await router_runtime.route_for_session(
        channel_id="channel-1",
        user_id="user-crisis",
        user_text="me quiero morir",
        pg_conn=None,
    )

    assert decision.model == router_runtime.CRISIS_MODEL
    assert decision.tier == "crisis"
    assert decision.reason == "crisis_trigger"
    assert decision.preset_mode == "respectful_serious"
    assert router_runtime.get_opus_count("user-crisis") == 1


async def test_route_for_session_resists_escalation_for_trivial_text_and_zero_disclosure():
    """Resistance: trivial text and disclosure zero stay out of crisis."""
    conn = AsyncMock()
    conn.fetchrow.return_value = {"s": 0}

    decision = await router_runtime.route_for_session(
        channel_id="channel-1",
        user_id="user-1",
        user_text="hola que tal",
        pg_conn=conn,
    )

    assert decision.model == router_runtime.CASUAL_MODEL
    assert decision.tier == "casual"
    assert decision.reason == "casual_preset"
    assert decision.preset_mode == "default_abrasive"
    assert decision.disclosure_severity == 0


async def test_route_for_session_classifier_exception_fails_open_to_depth():
    """Classifier exceptions fail open to the depth model without raising."""
    with patch.object(router_runtime, "classify_preset", side_effect=RuntimeError("boom")):
        decision = await router_runtime.route_for_session(
            channel_id="channel-1",
            user_id="user-1",
            user_text="hola que tal",
            pg_conn=None,
        )

    assert decision.model == router_runtime.DEPTH_MODEL
    assert decision.tier == "depth"
    assert decision.reason == "classifier_exception"
    assert decision.preset_mode == ""
    assert decision.disclosure_severity == 0
