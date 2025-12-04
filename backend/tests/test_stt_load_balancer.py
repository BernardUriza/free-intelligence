"""Test STT Load Balancer - Policy-Driven Architecture.

Tests:
  - Policy loading from policy.yaml
  - File size-based routing (>5MB → Deepgram)
  - Duration-based routing (>300s → Deepgram)
  - Forced provider override
  - Fallback mechanisms for empty transcripts
  - Performance tracking and adaptive selection
  - Stats reporting

Created: 2025-11-15
Updated: 2025-11-20 (Refactored for new policy-driven API)
Updated: 2025-01-XX (Azure Whisper removed - using Deepgram only)
"""

from __future__ import annotations

import pytest

from backend.utils.stt_load_balancer import STTLoadBalancer


class TestSTTLoadBalancer:
    """Test suite for policy-driven STT Load Balancer."""

    def test_policy_loading(self):
        """Test policy.yaml loading and default provider selection."""
        balancer = STTLoadBalancer()

        # Should load policy successfully
        assert balancer.policy is not None

        # Test default selection (should use primary_provider from policy)
        provider, reason = balancer.select_provider_for_file()

        assert provider == "deepgram"  # primary_provider from policy.yaml
        assert reason == "primary_provider"

    def test_file_size_routing(self):
        """Test file size-based routing (>5MB → Deepgram)."""
        balancer = STTLoadBalancer()

        # Small file (1MB) → deepgram (primary)
        provider, reason = balancer.select_provider_for_file(audio_size_bytes=1 * 1024 * 1024)
        assert provider == "deepgram"
        assert reason == "primary_provider"

        # Large file (6MB) → deepgram (policy routing - Azure removed)
        provider, reason = balancer.select_provider_for_file(audio_size_bytes=6 * 1024 * 1024)
        assert provider == "deepgram"  # Changed from azure_whisper
        assert "file_size" in reason
        assert "6.0MB" in reason

    def test_duration_routing(self):
        """Test duration-based routing (>300s → Deepgram)."""
        balancer = STTLoadBalancer()

        # Short audio (60s) → deepgram (primary)
        provider, reason = balancer.select_provider_for_file(duration_seconds=60)
        assert provider == "deepgram"
        assert reason == "primary_provider"

        # Long audio (400s) → deepgram (policy routing - Azure removed)
        provider, reason = balancer.select_provider_for_file(duration_seconds=400)
        assert provider == "deepgram"  # Changed from azure_whisper
        assert "duration" in reason
        assert "400s" in reason

    def test_forced_provider_override(self):
        """Test explicit provider override (highest priority)."""
        balancer = STTLoadBalancer()

        # Force deepgram even for small file (azure_whisper deprecated)
        provider, reason = balancer.select_provider_for_file(
            audio_size_bytes=1 * 1024 * 1024,  # Small file
            force_provider="deepgram",
        )
        assert provider == "deepgram"
        assert reason == "forced_by_request"

        # Force deepgram even for large file
        provider, reason = balancer.select_provider_for_file(
            audio_size_bytes=10 * 1024 * 1024,  # Large file
            force_provider="deepgram",
        )
        assert provider == "deepgram"
        assert reason == "forced_by_request"

    def test_fallback_for_empty_transcript(self):
        """Test fallback when provider returns empty transcript."""
        balancer = STTLoadBalancer()

        # Deepgram fails → deepgram (self-fallback, Azure removed)
        fallback = balancer.get_fallback_for_empty("deepgram")
        # Since Azure is removed, fallback should be None or deepgram itself
        assert fallback in [None, "deepgram"]

        # Azure fails → deepgram (if Azure still in config, otherwise None)
        fallback = balancer.get_fallback_for_empty("azure_whisper")
        # Should return None or deepgram since azure is deprecated
        assert fallback in [None, "deepgram"]

    def test_performance_recording(self):
        """Test performance metrics recording."""
        balancer = STTLoadBalancer()

        # Record some performance data
        balancer.record_performance(
            provider="deepgram",
            resolution_time=2.5,
            retry_attempts=0,
            failed=False,
        )

        balancer.record_performance(
            provider="deepgram",
            resolution_time=3.0,
            retry_attempts=1,
            failed=False,
        )

        balancer.record_performance(
            provider="deepgram",
            resolution_time=8.0,
            retry_attempts=0,
            failed=False,
        )

        # Check stats were recorded
        stats = balancer.get_stats()
        assert "performance" in stats
        assert "deepgram" in stats["performance"]

        # Verify averages (all deepgram now)
        deepgram_stats = stats["performance"]["deepgram"]
        assert deepgram_stats["avg_resolution_time"] == pytest.approx(3.5, rel=0.01)  # (2.5+3.0+8.0)/3
        assert deepgram_stats["avg_retries"] == pytest.approx(0.33, rel=0.01)  # (0+1+0)/3
        assert deepgram_stats["total_chunks"] == 3

    def test_adaptive_selection(self):
        """Test adaptive provider selection based on performance."""
        balancer = STTLoadBalancer()

        # Record poor performance for deepgram initially (slow + retries)
        for _ in range(3):
            balancer.record_performance(
                provider="deepgram",
                resolution_time=15.0,  # Slow (>10s threshold)
                retry_attempts=3,  # Many retries (>2 threshold)
                failed=False,
            )

        # Record good performance for deepgram later (simulating recovery)
        for _ in range(5):
            balancer.record_performance(
                provider="deepgram",
                resolution_time=2.0,
                retry_attempts=0,
                failed=False,
            )

        # Adaptive selection should choose deepgram (only provider available)
        provider, reason = balancer.select_provider_for_file(
            chunk_number=0,
            session_id="test_session_adaptive",
        )

        # Should use adaptive selection (deepgram is only option)
        assert provider == "deepgram"
        assert reason in ["adaptive_performance", "primary_provider"]

    def test_stats_reporting(self):
        """Test comprehensive stats reporting."""
        balancer = STTLoadBalancer()

        # Record some activity (only deepgram now)
        balancer.record_performance("deepgram", 2.0, 0, False)
        balancer.record_performance("deepgram", 5.0, 1, False)

        stats = balancer.get_stats()

        # Verify structure
        assert "policy" in stats
        assert "performance" in stats
        assert "session_preferences" in stats

        # Verify policy info
        assert stats["policy"]["primary_provider"] == "deepgram"
        assert stats["policy"]["large_file_threshold_mb"] == 5.0

        # Verify performance info (only deepgram)
        assert "deepgram" in stats["performance"]
        assert stats["performance"]["deepgram"]["total_chunks"] == 2
