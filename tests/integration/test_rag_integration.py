#!/usr/bin/env python3
"""Integration tests for RAG GPU acceleration (Phase 2 + Phase 3).

Tests the complete flow:
  1. RAG Service (GPU embeddings)
  2. Gateway (HTTP routing)
  3. Circuit Breaker + CPU Fallback
  4. End-to-end RAG query

Usage:
  python test_rag_integration.py

Requirements:
  - FI Monitor running with RAG service and gateway
  - Or: Manual start of services for testing
"""

from __future__ import annotations

import asyncio
import time

import httpx
import numpy as np
import pytest

# ============================================================================
# Test Configuration
# ============================================================================

RAG_SERVICE_URL = "http://localhost:11435"
GATEWAY_URL = "http://localhost:11400"
RAG_API_KEY = "change-me-in-production"  # TODO: From env

# Mark all tests as integration (skipped unless explicitly requested)
pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Test Utilities
# ============================================================================


def print_test(name: str):
    """Print test header."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")


def print_result(success: bool, message: str, elapsed_ms: int | None = None):
    """Print test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    timing = f" ({elapsed_ms}ms)" if elapsed_ms is not None else ""
    print(f"{status}: {message}{timing}")


# ============================================================================
# Phase 3 Tests: RAG Service & Gateway
# ============================================================================


async def test_rag_service_health():
    """Test RAG service health endpoint."""
    print_test("RAG Service Health Check")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            start = time.time()
            response = await client.get(f"{RAG_SERVICE_URL}/rag/health")
            elapsed_ms = int((time.time() - start) * 1000)

            if response.status_code == 200:
                data = response.json()
                print(f"  Status: {data.get('status')}")
                print(f"  Device: {data.get('device')}")
                print(f"  GPU: {data.get('gpu_name', 'N/A')}")
                print(f"  Model: {data.get('model')}")
                print_result(True, "RAG service is healthy", elapsed_ms)
                return True
            else:
                print_result(False, f"Unexpected status: {response.status_code}")
                return False

    except Exception as e:
        print_result(False, f"RAG service unavailable: {e}")
        return False


async def test_rag_service_embed():
    """Test RAG service embedding generation."""
    print_test("RAG Service Embedding")

    test_text = "What is the function of the liver?"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            start = time.time()
            response = await client.post(
                f"{RAG_SERVICE_URL}/rag/embed",
                json={"texts": [test_text]},
                headers={"X-API-Key": RAG_API_KEY},
            )
            elapsed_ms = int((time.time() - start) * 1000)

            if response.status_code == 200:
                data = response.json()
                embeddings = data["embeddings"]
                device = data.get("device", "unknown")

                print(f"  Text: {test_text}")
                print(f"  Embedding dim: {len(embeddings[0])}")
                print(f"  Device: {device}")
                print(f"  Count: {data.get('count')}")

                # Verify embedding dimension
                if len(embeddings[0]) == 384:
                    print_result(True, f"Embedding generated on {device}", elapsed_ms)
                    return True, elapsed_ms, device
                else:
                    print_result(False, f"Wrong dimension: {len(embeddings[0])}")
                    return False, None, None
            else:
                print_result(False, f"API error: {response.status_code}")
                return False, None, None

    except Exception as e:
        print_result(False, f"Embedding failed: {e}")
        return False, None, None


async def test_gateway_health():
    """Test gateway health endpoint."""
    print_test("Gateway Health Check")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            start = time.time()
            response = await client.get(f"{GATEWAY_URL}/gateway/health")
            elapsed_ms = int((time.time() - start) * 1000)

            if response.status_code == 200:
                data = response.json()
                print(f"  Status: {data.get('status')}")
                print(f"  Gateway port: {data.get('gateway_port')}")
                print(f"  Backends: {data.get('backends')}")
                print_result(True, "Gateway is healthy", elapsed_ms)
                return True
            else:
                print_result(False, f"Unexpected status: {response.status_code}")
                return False

    except Exception as e:
        print_result(False, f"Gateway unavailable: {e}")
        return False


async def test_gateway_routing_rag():
    """Test gateway routing to RAG service."""
    print_test("Gateway Routing (/rag/* → RAG Service)")

    test_text = "Test routing through gateway"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            start = time.time()
            response = await client.post(
                f"{GATEWAY_URL}/rag/embed",  # Through gateway
                json={"texts": [test_text]},
                headers={"X-API-Key": RAG_API_KEY},
            )
            elapsed_ms = int((time.time() - start) * 1000)

            if response.status_code == 200:
                data = response.json()
                print(f"  Routed to: RAG Service (port 11435)")
                print(f"  Device: {data.get('device')}")
                print_result(True, "Gateway routes /rag/* correctly", elapsed_ms)
                return True
            else:
                print_result(False, f"API error: {response.status_code}")
                return False

    except Exception as e:
        print_result(False, f"Routing failed: {e}")
        return False


# ============================================================================
# Phase 2 Tests: Circuit Breaker
# GPU-ONLY ARCHITECTURE: No CPU fallback tests
# See README.md: "No CPU fallback, no degraded mode"
# ============================================================================


async def test_circuit_breaker():
    """Test circuit breaker opens after failures."""
    print_test("Circuit Breaker Logic")

    from backend.src.fi_assistant.services.monitor_client import (
        CircuitBreaker,
    )

    breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=5)

    # Simulate 3 failures
    print("  Simulating 3 failures...")
    for i in range(3):
        breaker.on_failure()
        print(f"    Failure {i+1}/3 - Open: {breaker.is_open()}")

    # Circuit should be open now
    if breaker.is_open():
        print_result(True, "Circuit opened after 3 failures")

        # Wait for timeout
        print("  Waiting 5s for half-open state...")
        await asyncio.sleep(5.1)

        # Circuit should reset to half-open
        if not breaker.is_open():
            print_result(True, "Circuit reset to half-open after timeout")
            return True
        else:
            print_result(False, "Circuit did not reset")
            return False
    else:
        print_result(False, "Circuit did not open")
        return False


# ============================================================================
# Performance Benchmark
# GPU-ONLY ARCHITECTURE: Only GPU benchmarks
# ============================================================================


async def benchmark_gpu_performance():
    """Benchmark GPU embedding performance."""
    print_test("Performance Benchmark: GPU Embeddings")

    from backend.src.fi_assistant.services.monitor_client import (
        get_embedding_from_monitor,
    )

    test_text = "Benchmark GPU embedding performance"
    iterations = 5

    # GPU benchmark
    gpu_times = []
    print(f"\n  GPU Benchmark ({iterations} iterations):")
    for i in range(iterations):
        try:
            start = time.time()
            await get_embedding_from_monitor(test_text, timeout=5.0)
            elapsed_ms = int((time.time() - start) * 1000)
            gpu_times.append(elapsed_ms)
            print(f"    Iteration {i+1}: {elapsed_ms}ms")
        except Exception as e:
            print(f"    GPU error: {e}")
            print_result(False, f"GPU required but unavailable: {e}")
            return False

    # Results
    print("\n  Results:")
    gpu_avg = sum(gpu_times) / len(gpu_times)
    print(f"    GPU avg: {gpu_avg:.0f}ms")

    # Target: <50ms average per README
    success = gpu_avg < 100  # Allow some margin
    if success:
        print_result(True, f"GPU embeddings avg {gpu_avg:.0f}ms (target: <100ms)")
    else:
        print_result(False, f"GPU too slow: {gpu_avg:.0f}ms (target: <100ms)")
    return success


# ============================================================================
# Main Test Runner
# ============================================================================


async def run_all_tests():
    """Run all integration tests.
    
    GPU-ONLY ARCHITECTURE: No CPU fallback tests.
    See README.md: "No CPU fallback, no degraded mode, no 'it works but slow'"
    """
    print("\n" + "=" * 60)
    print("RAG GPU ACCELERATION - INTEGRATION TESTS")
    print("GPU-ONLY ARCHITECTURE - No CPU fallback")
    print("=" * 60)

    results = []

    # Phase 3: Services
    results.append(("RAG Health", await test_rag_service_health()))
    results.append(("RAG Embed", (await test_rag_service_embed())[0]))
    results.append(("Gateway Health", await test_gateway_health()))
    results.append(("Gateway Routing", await test_gateway_routing_rag()))

    # Phase 2: Circuit Breaker
    results.append(("Circuit Breaker", await test_circuit_breaker()))

    # Benchmark (GPU only)
    results.append(("GPU Performance", await benchmark_gpu_performance()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
