"""Tests for per-family pricing in cost accounting (insult.core.llm)."""

from __future__ import annotations

import pytest

from personas.insult.core import llm as llm_mod
from personas.insult.core.llm import _resolve_family, get_usage_report, record_usage


@pytest.fixture(autouse=True)
def _reset_usage():
    """Isolate tests: each starts with clean counters."""
    llm_mod._usage_by_family.clear()
    llm_mod._errors_total = 0
    yield
    llm_mod._usage_by_family.clear()
    llm_mod._errors_total = 0


def test_resolve_family_haiku():
    assert _resolve_family("claude-haiku-4-5-20251001") == "haiku"


def test_resolve_family_sonnet():
    assert _resolve_family("claude-sonnet-4-6") == "sonnet"


def test_resolve_family_opus():
    assert _resolve_family("claude-opus-4-7") == "opus"


def test_resolve_family_unknown_defaults_to_sonnet():
    # Conservative: unknown models are billed as Sonnet, not Haiku.
    assert _resolve_family("claude-gemini-42-alpha") == "sonnet"


def test_record_usage_splits_by_family():
    record_usage(1_000_000, 0, model="claude-haiku-4-5-20251001")
    record_usage(1_000_000, 0, model="claude-sonnet-4-6")
    report = get_usage_report()
    assert report["per_family"]["haiku"]["tokens"]["input_tokens"] == 1_000_000
    assert report["per_family"]["sonnet"]["tokens"]["input_tokens"] == 1_000_000
    # Haiku input = 1M * $1 = $1.00 ; Sonnet input = 1M * $3 = $3.00. Total = $4.00.
    assert report["cost_usd"]["total"] == pytest.approx(4.00, abs=0.01)
    assert report["per_family"]["haiku"]["cost_usd"] == pytest.approx(1.00, abs=0.01)
    assert report["per_family"]["sonnet"]["cost_usd"] == pytest.approx(3.00, abs=0.01)


def test_haiku_cheaper_than_sonnet_cheaper_than_opus():
    record_usage(1_000_000, 1_000_000, model="claude-haiku-4-5-20251001")
    haiku_cost = get_usage_report()["cost_usd"]["total"]
    llm_mod._usage_by_family.clear()

    record_usage(1_000_000, 1_000_000, model="claude-sonnet-4-6")
    sonnet_cost = get_usage_report()["cost_usd"]["total"]
    llm_mod._usage_by_family.clear()

    record_usage(1_000_000, 1_000_000, model="claude-opus-4-7")
    opus_cost = get_usage_report()["cost_usd"]["total"]

    assert haiku_cost < sonnet_cost < opus_cost


def test_empty_model_defaults_to_sonnet_bucket():
    record_usage(1_000_000, 0, model="")
    report = get_usage_report()
    assert "sonnet" in report["per_family"]
    assert report["per_family"]["sonnet"]["tokens"]["input_tokens"] == 1_000_000
