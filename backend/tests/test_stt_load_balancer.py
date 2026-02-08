"""Test STT Load Balancer - Policy-Driven Architecture.

Tests:
  - Policy loading from policy.yaml
  - File size-based routing
  - Duration-based routing
  - Forced provider override
  - Fallback mechanisms for empty transcripts
  - Performance tracking and adaptive selection
  - Stats reporting

Created: 2025-11-15
Updated: 2026-02-07 (Deepgram removed for PHI/HIPAA compliance, azure_whisper only)
"""

from __future__ import annotations

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

        assert provider == "azure_whisper"  # primary_provider from policy.yaml
        assert reason == "primary_provider"

    def test_file_size_routing(self):
        """Test file size-based routing."""
        balancer = STTLoadBalancer()

        # Small file (1MB) → azure_whisper (primary)
        provider, reason = balancer.select_provider_for_file(audio_size_bytes=1 * 1024 * 1024)
        assert provider == "azure_whisper"
        assert reason == "primary_provider"

        # Large file (6MB) → azure_whisper (policy routing)
        provider, reason = balancer.select_provider_for_file(audio_size_bytes=6 * 1024 * 1024)
        assert provider == "azure_whisper"
        assert "file_size" in reason
        assert "6.0MB" in reason

    def test_duration_routing(self):
        """Test duration-based routing."""
        balancer = STTLoadBalancer()

        # Short audio (60s) → azure_whisper (primary)
        provider, reason = balancer.select_provider_for_file(duration_seconds=60)
        assert provider == "azure_whisper"
        assert reason == "primary_provider"

        # Long audio (400s) → azure_whisper (policy routing)
        provider, reason = balancer.select_provider_for_file(duration_seconds=400)
        assert provider == "azure_whisper"
        assert "duration" in reason
        assert "400s" in reason

    def test_forced_provider_override(self):
        """Test explicit provider override (highest priority)."""
        balancer = STTLoadBalancer()

        # Force azure_whisper even for small file
        provider, reason = balancer.select_provider_for_file(
            audio_size_bytes=1 * 1024 * 1024,
            force_provider="azure_whisper",
        )
        assert provider == "azure_whisper"
        assert reason == "forced_by_request"

        # Force azure_whisper even for large file
        provider, reason = balancer.select_provider_for_file(
            audio_size_bytes=10 * 1024 * 1024,
            force_provider="azure_whisper",
        )
        assert provider == "azure_whisper"
        assert reason == "forced_by_request"

    def test_fallback_for_empty_transcript(self):
        """Test fallback when provider returns empty transcript."""
        balancer = STTLoadBalancer()

        # azure_whisper fails → no fallback (no fallback providers configured)
        fallback = balancer.get_fallback_for_empty("azure_whisper")
        assert fallback is None

    def test_performance_recording(self):
        """Test performance metrics recording."""
        balancer = STTLoadBalancer()

        # Record some performance data
        balancer.record_performance(
            provider="azure_whisper",
            resolution_time=2.5,
            retry_attempts=0,
            failed=False,
        )

        balancer.record_performance(
            provider="azure_whisper",
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
        assert "azure_whisper" in stats["performance"]

        # Verify averages
        whisper_stats = stats["performance"]["azure_whisper"]
        assert whisper_stats["avg_resolution_time"] == 4.5  # (2.5+3.0+8.0)/3
        assert whisper_stats["total_chunks"] == 3

    def test_adaptive_selection(self):
        """Test adaptive provider selection based on performance."""
        balancer = STTLoadBalancer()

        # Record poor performance initially (slow + retries)
        for _ in range(3):
            balancer.record_performance(
                provider="azure_whisper",
                resolution_time=15.0,
                retry_attempts=3,
                failed=False,
            )

        # Record good performance later (simulating recovery)
        for _ in range(5):
            balancer.record_performance(
                provider="azure_whisper",
                resolution_time=2.0,
                retry_attempts=0,
                failed=False,
            )

        # Adaptive selection should choose azure_whisper (only provider)
        provider, reason = balancer.select_provider_for_file(
            chunk_number=0,
            session_id="test_session_adaptive",
        )

        assert provider == "azure_whisper"
        assert reason in ["adaptive_performance", "primary_provider"]

    def test_stats_reporting(self):
        """Test comprehensive stats reporting."""
        balancer = STTLoadBalancer()

        # Record some activity
        balancer.record_performance("azure_whisper", 2.0, 0, False)
        balancer.record_performance("azure_whisper", 5.0, 1, False)

        stats = balancer.get_stats()

        # Verify structure
        assert "policy" in stats
        assert "performance" in stats
        assert "session_preferences" in stats

        # Verify policy info
        assert stats["policy"]["primary_provider"] == "azure_whisper"

        # Verify performance info
        assert "azure_whisper" in stats["performance"]
        assert stats["performance"]["azure_whisper"]["total_chunks"] == 2
