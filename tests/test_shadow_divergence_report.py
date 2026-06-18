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
