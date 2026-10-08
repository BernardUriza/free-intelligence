"""Weekly $5 spend cap for the gpt-4.1 host router (HOST 5/6).

Bernard's budget ($5/week, 2026-06-21) is a hard constraint, not advisory: the
router must fail SAFE once the cap is hit. These pin the cap, the per-call cost
math, and the ISO-week reset — plus the resistance case (a normal-traffic week
never trips, so the guard never silently kills routing under real load).
"""

from __future__ import annotations

from datetime import UTC, datetime

from demux_ai.router_budget import RouterBudget


def _at(y, mo, d):
    return datetime(y, mo, d, 12, 0, tzinfo=UTC)


def test_cost_math_uses_configured_rates():
    b = RouterBudget(weekly_cap_usd=5.0, input_per_mtok=2.0, output_per_mtok=8.0)
    # 115 in + 5 out  ->  115*2/1e6 + 5*8/1e6
    assert abs(b.cost_usd(115, 5) - (115 * 2 / 1_000_000 + 5 * 8 / 1_000_000)) < 1e-12


def test_under_cap_allows_spending():
    b = RouterBudget(weekly_cap_usd=5.0, input_per_mtok=2.0, output_per_mtok=8.0)
    assert b.can_spend() is True
    b.record(115, 5)  # ~$0.00027
    assert b.can_spend() is True
    assert b.spent_this_week() > 0


def test_cap_trips_and_fails_safe():
    # tiny cap so a couple of calls cross it
    b = RouterBudget(weekly_cap_usd=0.0005, input_per_mtok=2.0, output_per_mtok=8.0)
    assert b.can_spend() is True
    b.record(200, 50)  # 200*2/1e6 + 50*8/1e6 = 0.0008 > 0.0005
    assert b.can_spend() is False  # router now fails safe for the rest of the week


def test_week_rolls_resets_spend():
    clock = {"t": _at(2026, 6, 15)}  # ISO week N
    b = RouterBudget(weekly_cap_usd=0.0005, input_per_mtok=2.0, output_per_mtok=8.0, now=lambda: clock["t"])
    b.record(200, 50)
    assert b.can_spend() is False
    clock["t"] = _at(2026, 6, 23)  # next ISO week
    assert b.can_spend() is True  # reset
    assert b.spent_this_week() == 0.0


def test_realistic_week_never_trips():
    """RESISTANCE: hundreds of routing calls at the direct transport's ~115 tokens
    stay far under $5 — the guard must NOT silently kill routing under real load."""
    b = RouterBudget(weekly_cap_usd=5.0, input_per_mtok=2.0, output_per_mtok=8.0)
    for _ in range(500):
        if b.can_spend():
            b.record(115, 5)
    assert b.can_spend() is True
    assert b.spent_this_week() < 0.20  # 500 calls << $5
