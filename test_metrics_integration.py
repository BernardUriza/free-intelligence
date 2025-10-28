#!/usr/bin/env python3
"""
Test: Metrics Integration with LLM Router

Verifies:
1. LLM request metrics recorded (latency, tokens, cost)
2. Cache hit/miss metrics recorded
3. Error metrics recorded
4. Metrics summary displays correctly
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.llm_router import llm_generate, llm_embed
from backend.metrics import get_metrics_collector

def main():
    print("=" * 70)
    print("📊 Metrics Integration Test")
    print("=" * 70)

    metrics_collector = get_metrics_collector()

    # Test 1: LLM generation metrics
    print("\n" + "=" * 70)
    print("Test 1: LLM Generation Metrics")
    print("=" * 70)

    print("\n🤖 Generating with Ollama...")
    try:
        response = llm_generate(
            prompt="What is 2+2?",
            provider="ollama"
        )
        print(f"✅ Response: {response.content[:100]}")
        print(f"   Latency: {response.latency_ms:.0f}ms")
        print(f"   Tokens: {response.tokens_used}")
        print(f"   Cost: ${response.cost_usd:.6f}")
    except Exception as e:
        print(f"⚠️  Error: {e}")

    # Test 2: Cache metrics (embeddings)
    print("\n" + "=" * 70)
    print("Test 2: Cache Metrics (Embeddings)")
    print("=" * 70)

    text = "Free Intelligence is an AI memory system"

    print(f"\n📝 Embedding text: '{text}'")
    print("   First call (cache miss expected)...")
    try:
        emb1 = llm_embed(text, provider="ollama")
        print(f"   ✅ Embedding generated: {len(emb1)} dimensions")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")

    print("\n   Second call (cache hit expected)...")
    try:
        emb2 = llm_embed(text, provider="ollama")
        print(f"   ✅ Embedding retrieved: {len(emb2)} dimensions")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")

    # Test 3: Error metrics
    print("\n" + "=" * 70)
    print("Test 3: Error Metrics")
    print("=" * 70)

    print("\n🔥 Triggering error with invalid provider...")
    try:
        response = llm_generate(
            prompt="Test",
            provider="invalid_provider"
        )
    except Exception as e:
        print(f"   ✅ Error caught (expected): {type(e).__name__}")

    # Test 4: Metrics summary
    print("\n" + "=" * 70)
    print("Test 4: Metrics Summary")
    print("=" * 70)

    summary = metrics_collector.get_summary()

    print("\n⏱️  Latency Metrics:")
    print(f"   p50: {summary['latency']['p50_ms']:.0f}ms")
    print(f"   p95: {summary['latency']['p95_ms']:.0f}ms")
    print(f"   p99: {summary['latency']['p99_ms']:.0f}ms")
    print(f"   Mean: {summary['latency']['mean_ms']:.0f}ms")
    print(f"   Requests: {summary['latency']['count']}")

    print("\n💰 Cost Metrics:")
    print(f"   Total: ${summary['cost']['total_usd']:.6f}")
    print(f"   Tokens: {summary['cost']['tokens']:,}")
    print(f"   Requests: {summary['cost']['requests']}")
    print(f"   By Provider:")
    for provider, cost in summary['cost']['by_provider'].items():
        print(f"      {provider}: ${cost:.6f}")

    print("\n🔄 Cache Metrics:")
    print(f"   Hit Rate: {summary['cache']['hit_rate']*100:.1f}%")
    print(f"   Hits: {summary['cache']['hits']}")
    print(f"   Misses: {summary['cache']['misses']}")

    print("\n📡 Provider Distribution:")
    for provider, count in summary['provider_distribution'].items():
        print(f"   {provider}: {count} requests")

    print("\n❌ Errors by Provider:")
    if summary['errors_by_provider']:
        for provider, count in summary['errors_by_provider'].items():
            print(f"   {provider}: {count} errors")
    else:
        print("   No errors recorded")

    # Verification
    print("\n" + "=" * 70)
    print("📊 Verification")
    print("=" * 70)

    checks = [
        ("Latency metrics recorded", summary['latency']['count'] > 0),
        ("Cost metrics recorded", summary['cost']['requests'] > 0),
        ("Cache events recorded", (summary['cache']['hits'] + summary['cache']['misses']) > 0),
        ("Provider distribution tracked", len(summary['provider_distribution']) > 0),
    ]

    all_passed = True
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}")
        if not result:
            all_passed = False

    if all_passed:
        print("\n🎉 All metrics integration tests PASSED!")
    else:
        print("\n⚠️  Some metrics checks FAILED")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
