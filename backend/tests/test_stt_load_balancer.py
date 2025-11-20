"""Test STT Load Balancer - Policy-Driven Architecture.

Tests:
  - Policy loading from policy.yaml
  - File size-based routing (>5MB → Azure)
  - Duration-based routing (>300s → Azure)
  - Forced provider override
  - Fallback mechanisms for empty transcripts
  - Performance tracking and adaptive selection
  - Stats reporting

Created: 2025-11-15
Updated: 2025-11-20 (Refactored for new policy-driven API)
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
        """Test file size-based routing (>5MB → Azure)."""
        balancer = STTLoadBalancer()

        # Small file (1MB) → deepgram (primary)
        provider, reason = balancer.select_provider_for_file(audio_size_bytes=1 * 1024 * 1024)
        assert provider == "deepgram"
        assert reason == "primary_provider"

        # Large file (6MB) → azure_whisper (policy routing)
        provider, reason = balancer.select_provider_for_file(audio_size_bytes=6 * 1024 * 1024)
        assert provider == "azure_whisper"
        assert "file_size" in reason
        assert "6.0MB" in reason

    def test_duration_routing(self):
        """Test duration-based routing (>300s → Azure)."""
        balancer = STTLoadBalancer()

        # Short audio (60s) → deepgram (primary)
        provider, reason = balancer.select_provider_for_file(duration_seconds=60)
        assert provider == "deepgram"
        assert reason == "primary_provider"

        # Long audio (400s) → azure_whisper (policy routing)
        provider, reason = balancer.select_provider_for_file(duration_seconds=400)
        assert provider == "azure_whisper"
        assert "duration" in reason
        assert "400s" in reason

    def test_forced_provider_override(self):
        """Test explicit provider override (highest priority)."""
        balancer = STTLoadBalancer()

        # Force azure even for small file
        provider, reason = balancer.select_provider_for_file(
            audio_size_bytes=1 * 1024 * 1024,  # Small file
            force_provider="azure_whisper",
        )
        assert provider == "azure_whisper"
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

        # Deepgram fails → azure_whisper (from policy.yaml)
        fallback = balancer.get_fallback_for_empty("deepgram")
        assert fallback == "azure_whisper"

        # Azure fails → no fallback (only one fallback configured)
        fallback = balancer.get_fallback_for_empty("azure_whisper")
        # Should return None or empty since azure is last in chain
        assert fallback in [None, "deepgram"]  # Either no fallback or cycles back

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
            provider="azure_whisper",
            resolution_time=8.0,
            retry_attempts=0,
            failed=False,
        )

        # Check stats were recorded
        stats = balancer.get_stats()
        assert "performance" in stats
        assert "deepgram" in stats["performance"]
        assert "azure_whisper" in stats["performance"]

        # Verify averages
        deepgram_stats = stats["performance"]["deepgram"]
        assert deepgram_stats["avg_resolution_time"] == pytest.approx(2.75, rel=0.01)
        assert deepgram_stats["avg_retries"] == pytest.approx(0.5, rel=0.01)
        assert deepgram_stats["total_chunks"] == 2

        azure_stats = stats["performance"]["azure_whisper"]
        assert azure_stats["avg_resolution_time"] == pytest.approx(8.0, rel=0.01)
        assert azure_stats["total_chunks"] == 1

    def test_adaptive_selection(self):
        """Test adaptive provider selection based on performance."""
        balancer = STTLoadBalancer()

        # Record poor performance for deepgram (slow + retries)
        for _ in range(5):
            balancer.record_performance(
                provider="deepgram",
                resolution_time=15.0,  # Slow (>10s threshold)
                retry_attempts=3,  # Many retries (>2 threshold)
                failed=False,
            )

        # Record good performance for azure_whisper
        for _ in range(5):
            balancer.record_performance(
                provider="azure_whisper",
                resolution_time=2.0,
                retry_attempts=0,
                failed=False,
            )

        # Adaptive selection should choose azure_whisper despite deepgram being primary
        provider, reason = balancer.select_provider_for_file(
            chunk_number=0,
            session_id="test_session_adaptive",
        )

        # Should use adaptive selection (azure_whisper has better performance)
        assert provider == "azure_whisper"
        assert reason == "adaptive_performance"

    def test_stats_reporting(self):
        """Test comprehensive stats reporting."""
        balancer = STTLoadBalancer()

        # Record some activity
        balancer.record_performance("deepgram", 2.0, 0, False)
        balancer.record_performance("azure_whisper", 5.0, 1, False)

        stats = balancer.get_stats()

        # Verify structure
        assert "policy" in stats
        assert "performance" in stats
        assert "session_preferences" in stats

        # Verify policy info
        assert stats["policy"]["primary_provider"] == "deepgram"
        assert stats["policy"]["large_file_threshold_mb"] == 5.0

        # Verify performance info
        assert "deepgram" in stats["performance"]
        assert "azure_whisper" in stats["performance"]
