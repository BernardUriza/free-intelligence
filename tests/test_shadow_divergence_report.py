"""Tests for the pure logic of scripts/shadow_divergence_report.py — the bucketer
that classifies shadow_router_decision rows for the slice-B measurement gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "shadow_divergence_report",
    Path(__file__).resolve().parent.parent / "scripts" / "shadow_divergence_report.py",
)
assert _spec is not None and _spec.loader is not None
sdr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sdr)


def test_default_insult_agreement_is_default_bucket():
    assert (
        sdr.classify_decision(
            shadow_reason="default_insult",
            diverged="false",
        )
        == sdr.BUCKET_AGREE_INSULT
    )


def test_explicit_vultur_agreement_is_its_own_bucket():
    assert (
        sdr.classify_decision(
            shadow_reason="vultur_prefix",
            diverged="false",
        )
        == sdr.BUCKET_AGREE_VULTUR
    )


def test_divergence_always_wins_even_with_benign_reason():
    # A diverged row must surface for review even if its reason looks ordinary —
    # it must NOT be hidden in an "agree" bucket.
    assert (
        sdr.classify_decision(
            shadow_reason="default_insult",
            diverged="true",
        )
        == sdr.BUCKET_DIVERGED
    )


def test_diverged_accepts_bool_and_string():
    assert sdr._as_bool(True) is True
    assert sdr._as_bool("true") is True
    assert sdr._as_bool("True") is True
    assert sdr._as_bool("false") is False
    assert sdr._as_bool(False) is False
    assert sdr._as_bool("") is False


def test_summarize_counts_by_bucket():
    rows = [
        {"current": "insult", "shadow": "insult", "reason": "default_insult", "diverged": "false"},
        {"current": "insult", "shadow": "insult", "reason": "default_insult", "diverged": "false"},
        {"current": "vultur", "shadow": "vultur", "reason": "vultur_prefix", "diverged": "false"},
        {"current": "insult", "shadow": "vultur", "reason": "vultur_prefix", "diverged": "true"},
    ]
    counts = sdr.summarize(rows)
    assert counts[sdr.BUCKET_AGREE_INSULT] == 2
    assert counts[sdr.BUCKET_AGREE_VULTUR] == 1
    assert counts[sdr.BUCKET_DIVERGED] == 1


def test_build_query_targets_the_shadow_event():
    q = sdr.build_query(72)
    assert "shadow_router_decision" in q
    assert "ago(72h)" in q


def test_general_channel_id_constant():
    # The #general channel is the record-grade verification surface (testing.md).
    assert sdr.GENERAL_CHANNEL_ID == "1489180895264116736"


def test_partition_by_channel_splits_general_from_dm():
    # slice A.1 — the report must filter #general FOR REAL: a DM turn
    # (channel 1489130575422820352) must NOT be counted as #general evidence.
    rows = [
        {"channel": "1489180895264116736", "reason": "default_insult", "diverged": "false"},
        {"channel": "1489130575422820352", "reason": "default_insult", "diverged": "false"},
    ]
    in_ch, off = sdr.partition_by_channel(rows, sdr.GENERAL_CHANNEL_ID)
    assert [r["channel"] for r in in_ch] == ["1489180895264116736"]
    assert [r["channel"] for r in off] == ["1489130575422820352"]


def test_partition_by_channel_all_off_channel_yields_empty_in_channel():
    # The real state today: shadow traffic exists but NONE in #general — the
    # report must distinguish "no #general traffic" from "no traffic at all".
    rows = [
        {"channel": "1489130575422820352", "reason": "default_insult", "diverged": "false"},
        {"channel": "1489130575422820352", "reason": "default_insult", "diverged": "false"},
    ]
    in_ch, off = sdr.partition_by_channel(rows, sdr.GENERAL_CHANNEL_ID)
    assert in_ch == []
    assert len(off) == 2


def test_build_query_projects_slice_a1_fields():
    # slice A.1 telemetry hardening: the report must read channel, guild,
    # explicit_vultur_trigger and route_input_len, not just the 4 slice-A fields.
    q = sdr.build_query(24)
    for field in ("channel", "guild", "explicit_vultur_trigger", "route_input_len"):
        assert field in q


# --- slice A.2: gpt-4.1 LLM shadow — the GENUINE divergence taxonomy -----------


def test_llm_query_targets_the_llm_shadow_event():
    q = sdr.build_llm_query(96)
    assert "llm_shadow_router_decision" in q
    assert "ago(96h)" in q
    for field in ("llm_shadow_target", "llm_diverged", "current"):
        assert field in q


def test_classify_llm_agreement_when_brain_matches_live():
    assert (
        sdr.classify_llm_decision(current_target="insult", llm_shadow_target="insult", llm_diverged="false")
        == sdr.LLM_BUCKET_AGREE
    )


def test_classify_llm_missing_vultur():
    # live sent it to Insult, the host brain says Vultur → a "should have been
    # Vultur" candidate. The signal the deterministic shadow can NEVER produce.
    assert (
        sdr.classify_llm_decision(current_target="insult", llm_shadow_target="vultur", llm_diverged="true")
        == sdr.LLM_BUCKET_MISSING_VULTUR
    )


def test_classify_llm_false_vultur():
    # the ~vultur prefix sent it to Vultur, the brain says Insult → a "didn't
    # need Vultur" candidate.
    assert (
        sdr.classify_llm_decision(current_target="vultur", llm_shadow_target="insult", llm_diverged="true")
        == sdr.LLM_BUCKET_FALSE_VULTUR
    )


def test_summarize_llm_counts_by_bucket():
    rows = [
        {"current": "insult", "llm_shadow_target": "insult", "llm_diverged": "false"},
        {"current": "insult", "llm_shadow_target": "vultur", "llm_diverged": "true"},
        {"current": "vultur", "llm_shadow_target": "insult", "llm_diverged": "true"},
    ]
    counts = sdr.summarize_llm(rows)
    assert counts[sdr.LLM_BUCKET_AGREE] == 1
    assert counts[sdr.LLM_BUCKET_MISSING_VULTUR] == 1
    assert counts[sdr.LLM_BUCKET_FALSE_VULTUR] == 1


# --- HOST 5/6 slice-B readiness gate (coagent flip criteria 2026-06-21) --------


def test_classify_parse_quality_clean_loose_unparseable():
    assert sdr.classify_parse_quality("llm_vultur") == sdr.PARSE_CLEAN
    assert sdr.classify_parse_quality("llm_insult") == sdr.PARSE_CLEAN
    assert sdr.classify_parse_quality("llm_vultur_loose") == sdr.PARSE_LOOSE
    assert sdr.classify_parse_quality("llm_unparseable") == sdr.PARSE_UNPARSEABLE


def test_percentile_empty_and_single():
    assert sdr.percentile([], 95) == 0.0
    assert sdr.percentile([115], 95) == 115.0


def test_percentile_p95_interpolates():
    # 1..100 → p95 lands at 95.05 by linear interpolation (NIST/numpy 'linear').
    values = list(range(1, 101))
    assert abs(sdr.percentile(values, 95) - 95.05) < 1e-9


def test_percentile_catches_token_bloat_tail():
    # p95 tolerates ~5% outliers by design; a bloat REGRESSION worth catching is
    # sustained (>=10% of calls). At 10% bloated, p95 jumps off the clean floor —
    # exactly the signal that the agentic transport leaked back onto the direct path.
    healthy = [115] * 20
    assert sdr.percentile(healthy, 95) == 115.0
    regressed = [115] * 18 + [9507] * 2
    assert sdr.percentile(regressed, 95) > 1000


def test_estimate_window_spend_uses_live_price_model():
    # priced via demux_ai.router_budget ($2/Mtok in, $8/Mtok out) — no parallel table.
    rows = [{"llm_input_tokens": "1000000", "llm_output_tokens": "1000000"}]
    assert abs(sdr.estimate_window_spend_usd(rows) - (2.00 + 8.00)) < 1e-9


def test_count_router_errors_and_timeouts():
    ops = [
        {"event": "llm_shadow_router_failed", "exc": "asyncio.TimeoutError: timed out"},
        {"event": "llm_shadow_router_failed", "exc": "BackendError: codex CLI not on PATH"},
        {"event": "llm_router_spend", "week_spent_usd": "0.01"},
    ]
    assert sdr.count_router_errors(ops) == 2
    assert sdr.count_timeouts(ops) == 1


def test_observed_week_spend_takes_max_counter_and_cap():
    ops = [
        {"event": "llm_router_spend", "week_spent_usd": "0.01", "cap_usd": "5.0"},
        {"event": "llm_router_spend", "week_spent_usd": "0.03", "cap_usd": "5.0"},
    ]
    spend, cap = sdr.observed_week_spend(ops, cap_default=5.0)
    assert spend == 0.03
    assert cap == 5.0


def test_observed_week_spend_defaults_cap_when_absent():
    spend, cap = sdr.observed_week_spend([], cap_default=5.0)
    assert spend == 0.0
    assert cap == 5.0


def test_readiness_verdict_waits_below_min_samples():
    v = sdr.readiness_verdict(
        general_llm_count=3,
        false_vultur=0,
        missing_vultur=1,
        router_error=0,
        timeout=0,
        parse_unparseable=0,
        observed_week_spend_usd=0.01,
        cap_usd=5.0,
    )
    assert v["overall"] == "WAIT_MORE_SAMPLES"


def test_readiness_verdict_red_on_hard_failure():
    v = sdr.readiness_verdict(
        general_llm_count=100,
        false_vultur=0,
        missing_vultur=2,
        router_error=4,  # recurrent router error = hard FAIL → RED
        timeout=0,
        parse_unparseable=0,
        observed_week_spend_usd=0.01,
        cap_usd=5.0,
    )
    assert v["overall"] == "RED"


def test_readiness_verdict_red_on_overspend():
    v = sdr.readiness_verdict(
        general_llm_count=100,
        false_vultur=0,
        missing_vultur=0,
        router_error=0,
        timeout=0,
        parse_unparseable=0,
        observed_week_spend_usd=5.5,  # over the cap
        cap_usd=5.0,
    )
    assert v["overall"] == "RED"


def test_readiness_verdict_green_pending_manual_never_unqualified_green():
    # all auto-criteria pass, enough samples → GREEN_PENDING_MANUAL, NOT "GREEN":
    # the kill-switch + fallback proofs stay MANUAL (Art. 2 — never green on unrun).
    v = sdr.readiness_verdict(
        general_llm_count=80,
        false_vultur=0,
        missing_vultur=3,
        router_error=0,
        timeout=0,
        parse_unparseable=0,
        observed_week_spend_usd=0.02,
        cap_usd=5.0,
    )
    assert v["overall"] == "GREEN_PENDING_MANUAL"
    manual = [c for c in v["criteria"] if c["status"] == "MANUAL"]
    assert {c["name"] for c in manual} == {"kill_switch_tested", "deterministic_fallback_tested"}


def test_readiness_verdict_false_vultur_is_review_not_silent_pass():
    # a nonzero false_vultur must surface as REVIEW, never hide in a PASS.
    v = sdr.readiness_verdict(
        general_llm_count=80,
        false_vultur=2,
        missing_vultur=0,
        router_error=0,
        timeout=0,
        parse_unparseable=0,
        observed_week_spend_usd=0.02,
        cap_usd=5.0,
    )
    fv = next(c for c in v["criteria"] if c["name"] == "false_vultur")
    assert fv["status"] == "REVIEW"


def test_build_llm_ops_query_targets_ops_events():
    q = sdr.build_llm_ops_query(48)
    assert "ago(48h)" in q
    for ev in ("llm_shadow_router_failed", "llm_router_spend", "llm_router_budget_exceeded"):
        assert ev in q
