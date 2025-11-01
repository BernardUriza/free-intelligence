#!/usr/bin/env python3
"""
End-to-End Test: Gatekeeper with Ollama Integration

Tests complete flow:
1. Ollama generates response
2. Gatekeeper scores quality
3. Fallback to Claude if score < 70 (simulated)
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.gatekeeper import Gatekeeper, QualityScorer
from backend.llm_router import llm_generate


def main():
    print("=" * 70)
    print("🚦 Gatekeeper End-to-End Test")
    print("=" * 70)

    gatekeeper = Gatekeeper()
    scorer = QualityScorer()

    # Test 1: Good quality response (should pass)
    print("\n" + "=" * 70)
    print("Test 1: Alice in Wonderland (Expected: PASS, score > 70)")
    print("=" * 70)

    prompt1 = "Who is Alice in Alice in Wonderland? Answer in 2-3 sentences."
    print(f"\n💬 Prompt: {prompt1}")

    print("\n🤖 Generating with Ollama...")
    response1 = llm_generate(prompt=prompt1, provider="ollama")

    print(f"\n📝 Response ({len(response1.content)} chars):")
    print(f"  {response1.content}")

    print(f"\n⏱️  Generation time: {response1.latency_ms/1000:.1f}s")
    print(f"💰 Cost: ${response1.cost_usd:.6f}")

    print("\n🧮 Scoring response...")
    quality_score1 = scorer.score_response(prompt1, response1.content, "ollama")

    print(f"\n📊 Quality Score: {quality_score1.total_score}/100")
    print(f"  {quality_score1.explanation}")
    print(
        f"  Breakdown: Length={quality_score1.length_score}/30, "
        f"Keywords={quality_score1.keyword_score}/30, "
        f"Coherence={quality_score1.coherence_score}/20, "
        f"Completeness={quality_score1.completeness_score}/20"
    )

    if quality_score1.total_score >= 70:
        print("\n✅ PASS: Quality score above threshold (70)")
        print("   Decision: Keep Ollama response (fast, free, private)")
    else:
        print(f"\n⚠️  FAIL: Quality score {quality_score1.total_score} < 70")
        print("   Decision: Would fallback to Claude API (but skipped in test)")

    # Test 2: Simple math (might be low quality)
    print("\n\n" + "=" * 70)
    print("Test 2: Simple Question (Expected: might fail quality check)")
    print("=" * 70)

    prompt2 = "What is the capital of France?"
    print(f"\n💬 Prompt: {prompt2}")

    print("\n🤖 Generating with Ollama...")
    response2 = llm_generate(prompt=prompt2, provider="ollama")

    print(f"\n📝 Response ({len(response2.content)} chars):")
    print(f"  {response2.content}")

    print("\n🧮 Scoring response...")
    quality_score2 = scorer.score_response(prompt2, response2.content, "ollama")

    print(f"\n📊 Quality Score: {quality_score2.total_score}/100")
    print(f"  {quality_score2.explanation}")

    if quality_score2.total_score >= 70:
        print("\n✅ PASS: Quality score above threshold")
        print("   Decision: Keep Ollama response")
    else:
        print(f"\n⚠️  FAIL: Quality score {quality_score2.total_score} < 70")
        print("   Decision: Would fallback to Claude API")

    # Summary
    print("\n\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)

    print(
        f"\nTest 1 (Alice): {quality_score1.total_score}/100 - "
        + ("✅ PASS" if quality_score1.total_score >= 70 else "❌ FAIL")
    )
    print(
        f"Test 2 (Capital): {quality_score2.total_score}/100 - "
        + ("✅ PASS" if quality_score2.total_score >= 70 else "❌ FAIL")
    )

    print("\n🚦 Gatekeeper Behavior:")
    print("  - Scores >= 70: Use Ollama (fast, free, private)")
    print("  - Scores < 70:  Fallback to Claude (higher quality)")
    print("\n💡 Progressive Rollout:")
    print("  - Phase 1 (10% Ollama): Conservative start")
    print("  - Phase 2 (50% Ollama): If avg score > 75 for 7 days")
    print("  - Phase 3 (100% Ollama): If avg score > 85 for 7 days")

    print("\n" + "=" * 70)
    print("🎉 Gatekeeper E2E Test Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
