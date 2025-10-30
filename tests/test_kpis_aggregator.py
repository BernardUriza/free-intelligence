"""
Tests for KPIs aggregator.

File: tests/test_kpis_aggregator.py
Created: 2025-10-30
Card: FI-API-FEAT-011
"""

import time

import pytest

from backend.kpis_aggregator import KPIsAggregator


@pytest.fixture
def aggregator():
    """Create fresh aggregator for each test."""
    return KPIsAggregator(bucket_sec=10, retention_min=60)


def test_record_http_event(aggregator):
    """Test recording HTTP events."""
    aggregator.record_http_event(
        route="/api/sessions",
        status=200,
        duration_ms=150,
    )

    summary = aggregator.get_summary(window="1m")
    assert summary["requests"]["total"] == 1
    assert summary["requests"]["2xx"] == 1
    assert summary["latency"]["p95_ms"] == 150


def test_record_llm_event(aggregator):
    """Test recording LLM events."""
    aggregator.record_llm_event(
        provider="anthropic",
        tokens_in=100,
        tokens_out=200,
        latency_ms=500,
        cache_hit=False,
    )

    summary = aggregator.get_summary(window="1m")
    assert summary["tokens"]["in"] == 100
    assert summary["tokens"]["out"] == 200
    assert summary["cache"]["miss"] == 1
    assert summary["providers"][0]["id"] == "anthropic"


def test_cache_hit_metrics(aggregator):
    """Test cache hit recording."""
    # Miss
    aggregator.record_llm_event(
        provider="openai",
        tokens_in=50,
        tokens_out=100,
        latency_ms=300,
        cache_hit=False,
    )

    # Hit
    aggregator.record_llm_event(
        provider="openai",
        tokens_in=50,
        tokens_out=100,
        latency_ms=0,
        cache_hit=True,
    )

    summary = aggregator.get_summary(window="1m")
    assert summary["cache"]["hit"] == 1
    assert summary["cache"]["miss"] == 1
    assert summary["cache"]["hit_ratio"] == 0.5


def test_unknown_tokens(aggregator):
    """Test handling of unknown tokens."""
    aggregator.record_llm_event(
        provider="local",
        tokens_in=None,  # Unknown
        tokens_out=None,  # Unknown
        latency_ms=200,
        cache_hit=False,
    )

    summary = aggregator.get_summary(window="1m")
    assert summary["tokens"]["in"] == 0
    assert summary["tokens"]["out"] == 0
    assert summary["tokens"]["unknown"] == 2  # Both in and out


def test_multiple_providers(aggregator):
    """Test provider distribution."""
    aggregator.record_llm_event(provider="anthropic", latency_ms=100)
    aggregator.record_llm_event(provider="anthropic", latency_ms=110)
    aggregator.record_llm_event(provider="openai", latency_ms=120)
    aggregator.record_llm_event(provider="local", latency_ms=90)

    summary = aggregator.get_summary(window="1m")
    providers = {p["id"]: p for p in summary["providers"]}

    assert providers["anthropic"]["count"] == 2
    assert providers["anthropic"]["pct"] == 0.5
    assert providers["openai"]["count"] == 1
    assert providers["openai"]["pct"] == 0.25
    assert providers["local"]["count"] == 1
    assert providers["local"]["pct"] == 0.25


def test_p95_calculation(aggregator):
    """Test p95 latency calculation."""
    # Record 20 samples (0-19ms)
    for i in range(20):
        aggregator.record_http_event(
            route="/api/test",
            status=200,
            duration_ms=i,
        )

    summary = aggregator.get_summary(window="1m")
    # p95 of 0-19 should be 19 (95th percentile index = 19)
    assert summary["latency"]["p95_ms"] == 19


def test_window_filtering(aggregator):
    """Test time window filtering."""
    # Record event now
    aggregator.record_http_event(
        route="/api/recent",
        status=200,
        duration_ms=100,
    )

    # Get summary for 1m window
    summary_1m = aggregator.get_summary(window="1m")
    assert summary_1m["requests"]["total"] == 1

    # Get summary for 5m window
    summary_5m = aggregator.get_summary(window="5m")
    assert summary_5m["requests"]["total"] == 1


def test_chips_format(aggregator):
    """Test chips output format."""
    aggregator.record_llm_event(
        provider="anthropic",
        tokens_in=100,
        tokens_out=200,
        latency_ms=150,
        cache_hit=False,
    )

    chips = aggregator.get_chips(window="5m")

    assert chips["window"] == "5m"
    assert "asOf" in chips
    assert len(chips["chips"]) == 5

    # Check chip structure
    chip_ids = {c["id"] for c in chips["chips"]}
    assert "tokens_in" in chip_ids
    assert "tokens_out" in chip_ids
    assert "p95_ms" in chip_ids
    assert "cache_hit" in chip_ids
    assert "provider_mix" in chip_ids

    # Validate tokens_in chip
    tokens_in_chip = next(c for c in chips["chips"] if c["id"] == "tokens_in")
    assert tokens_in_chip["value"] == 100
    assert tokens_in_chip["unit"] == "tok"


def test_timeseries_format(aggregator):
    """Test timeseries output format."""
    # Record multiple events across time
    for i in range(5):
        aggregator.record_llm_event(
            provider="anthropic",
            tokens_in=100,
            tokens_out=200,
            latency_ms=150 + i * 10,
            cache_hit=False,
        )
        time.sleep(0.01)  # Small delay to spread across buckets

    timeseries = aggregator.get_timeseries(window="15m")

    assert timeseries["window"] == "15m"
    assert "asOf" in timeseries
    assert timeseries["bucketSec"] == 10

    # Check series structure
    series = timeseries["series"]
    assert "p95_ms" in series
    assert "tokens_in" in series
    assert "tokens_out" in series
    assert "cache_hit_ratio" in series

    # Each series should be array of [timestamp, value] pairs
    assert isinstance(series["p95_ms"], list)
    if series["p95_ms"]:
        assert len(series["p95_ms"][0]) == 2  # [ts, value]


def test_empty_summary(aggregator):
    """Test empty summary when no data."""
    summary = aggregator.get_summary(window="1m")

    assert summary["requests"]["total"] == 0
    assert summary["latency"]["p95_ms"] == 0
    assert summary["tokens"]["in"] == 0
    assert summary["cache"]["hit_ratio"] == 0.0
    assert summary["providers"] == []


def test_http_status_codes(aggregator):
    """Test HTTP status code tracking."""
    aggregator.record_http_event(route="/api/success", status=200, duration_ms=100)
    aggregator.record_http_event(route="/api/created", status=201, duration_ms=110)
    aggregator.record_http_event(route="/api/notfound", status=404, duration_ms=50)
    aggregator.record_http_event(route="/api/error", status=500, duration_ms=200)

    summary = aggregator.get_summary(window="1m")
    assert summary["requests"]["total"] == 4
    assert summary["requests"]["2xx"] == 2
    assert summary["requests"]["4xx"] == 1
    assert summary["requests"]["5xx"] == 1


def test_bucket_cleanup(aggregator):
    """Test bucket cleanup after retention window."""
    # Record event
    aggregator.record_http_event(
        route="/api/old",
        status=200,
        duration_ms=100,
    )

    assert len(aggregator.buckets) == 1

    # Simulate retention window expiry by manipulating bucket timestamps
    old_buckets = list(aggregator.buckets.keys())
    for bucket_ts in old_buckets:
        bucket = aggregator.buckets[bucket_ts]
        bucket.start_ts = time.time() - (aggregator.retention_sec + 100)
        bucket.end_ts = bucket.start_ts + aggregator.bucket_sec
        # Update bucket key to match old timestamp
        del aggregator.buckets[bucket_ts]
        aggregator.buckets[bucket.start_ts] = bucket

    # Force cleanup
    aggregator.last_cleanup_ts = 0  # Reset to force cleanup
    aggregator._cleanup_if_needed()

    # Old bucket should be cleaned up
    assert len(aggregator.buckets) == 0

    # Record new event after cleanup
    aggregator.record_http_event(
        route="/api/new",
        status=200,
        duration_ms=100,
    )

    summary = aggregator.get_summary(window="24h")
    assert summary["requests"]["total"] == 1  # Only new event


def test_performance_p95_calculation():
    """Test p95 calculation performance (<10ms requirement)."""
    aggregator = KPIsAggregator()

    # Record 1000 events
    for i in range(1000):
        aggregator.record_http_event(
            route="/api/perf",
            status=200,
            duration_ms=i % 500,  # 0-499ms range
        )

    # Measure p95 calculation time
    start = time.time()
    summary = aggregator.get_summary(window="5m")
    elapsed_ms = (time.time() - start) * 1000

    assert summary["latency"]["p95_ms"] > 0
    assert elapsed_ms < 10.0  # Must be under 10ms
