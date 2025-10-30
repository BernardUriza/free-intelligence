#!/usr/bin/env python3
"""
Free Intelligence - Sessions API p95 Latency Benchmark

Measures p95 latency for GET /api/sessions (list endpoint).

File: tests/benchmark_sessions_p95.py
Card: FI-API-FEAT-009
Created: 2025-10-29

Requirements:
- API must be running (uvicorn backend.api.sessions:router)
- 20 samples minimum for statistical significance

Target: p95 < 200ms
"""

import statistics
import sys
import time

import requests


def measure_p95_latency(url: str, num_samples: int = 20):
    """
    Measure p95 latency for Sessions API list endpoint.

    Args:
        url: API endpoint URL
        num_samples: Number of samples to collect

    Returns:
        dict with metrics (p50, p95, p99, mean, min, max)
    """
    latencies = []

    print(f"Measuring latency for {url} ({num_samples} samples)...")

    for i in range(num_samples):
        start = time.time()
        try:
            response = requests.get(url, timeout=5)
            elapsed_ms = (time.time() - start) * 1000

            if response.status_code == 200:
                latencies.append(elapsed_ms)
                print(f"  Sample {i+1}/{num_samples}: {elapsed_ms:.2f}ms")
            else:
                print(f"  Sample {i+1}/{num_samples}: ERROR {response.status_code}")
                sys.exit(1)

        except Exception as e:
            print(f"  Sample {i+1}/{num_samples}: EXCEPTION {e}")
            sys.exit(1)

    if not latencies:
        print("ERROR: No successful samples collected")
        sys.exit(1)

    # Calculate percentiles
    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)

    p50_idx = int(n * 0.50)
    p95_idx = min(int(n * 0.95), n - 1)
    p99_idx = min(int(n * 0.99), n - 1)

    metrics = {
        "samples": n,
        "mean": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "p50": latencies_sorted[p50_idx],
        "p95": latencies_sorted[p95_idx],
        "p99": latencies_sorted[p99_idx],
        "min": min(latencies),
        "max": max(latencies),
    }

    return metrics


def main():
    """Run p95 benchmark"""
    # Note: For CI, would use TestClient instead of live server
    # For now, assume API is running locally
    url = "http://localhost:8000/api/sessions"

    print("=" * 70)
    print("Sessions API p95 Latency Benchmark")
    print("=" * 70)

    # Check if API is reachable
    try:
        response = requests.get(url, timeout=2)
        if response.status_code != 200:
            print(f"\nERROR: API returned {response.status_code}")
            print("Start API with: uvicorn backend.api.sessions:router --reload")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("\nERROR: Cannot connect to API")
        print("Start API with: uvicorn backend.api.sessions:router --reload")
        sys.exit(1)

    # Run benchmark
    metrics = measure_p95_latency(url, num_samples=20)

    # Print results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Samples:   {metrics['samples']}")
    print(f"Mean:      {metrics['mean']:.2f}ms")
    print(f"Median:    {metrics['median']:.2f}ms")
    print(f"p50:       {metrics['p50']:.2f}ms")
    print(f"p95:       {metrics['p95']:.2f}ms ⭐")
    print(f"p99:       {metrics['p99']:.2f}ms")
    print(f"Min:       {metrics['min']:.2f}ms")
    print(f"Max:       {metrics['max']:.2f}ms")
    print("=" * 70)

    # Check target
    target_p95 = 200.0
    if metrics["p95"] < target_p95:
        print(f"\n✅ PASS: p95 {metrics['p95']:.2f}ms < {target_p95}ms target")
        sys.exit(0)
    else:
        print(f"\n❌ FAIL: p95 {metrics['p95']:.2f}ms >= {target_p95}ms target")
        sys.exit(1)


if __name__ == "__main__":
    main()
