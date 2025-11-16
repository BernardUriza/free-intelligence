"""Test STT Load Balancer.

Tests:
  - Provider detection from environment
  - Round-robin selection
  - Deterministic chunk-based selection
  - Fallback handling

Created: 2025-11-15
"""

from __future__ import annotations

import os

import pytest

from backend.utils.stt_load_balancer import STTLoadBalancer


class TestSTTLoadBalancer:
    """Test suite for STT Load Balancer."""

    def test_provider_detection(self):
        """Test auto-detection of available providers."""
        # Should detect both if both env vars set
        balancer = STTLoadBalancer()

        has_azure = bool(os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_KEY"))
        has_deepgram = bool(os.getenv("DEEPGRAM_API_KEY"))

        if has_azure and has_deepgram:
            assert len(balancer.providers) == 2
            assert "azure_whisper" in balancer.providers
            assert "deepgram" in balancer.providers
        elif has_azure:
            assert len(balancer.providers) == 1
            assert "azure_whisper" in balancer.providers
        elif has_deepgram:
            assert len(balancer.providers) == 1
            assert "deepgram" in balancer.providers

    def test_round_robin_deterministic(self):
        """Test deterministic round-robin based on chunk number."""
        balancer = STTLoadBalancer(providers=["azure_whisper", "deepgram"])

        # Chunk 0 → azure_whisper
        assert balancer.select_provider(chunk_number=0) == "azure_whisper"

        # Chunk 1 → deepgram
        assert balancer.select_provider(chunk_number=1) == "deepgram"

        # Chunk 2 → azure_whisper (wraps around)
        assert balancer.select_provider(chunk_number=2) == "azure_whisper"

        # Chunk 3 → deepgram
        assert balancer.select_provider(chunk_number=3) == "deepgram"

    def test_round_robin_sequential(self):
        """Test sequential round-robin (no chunk number)."""
        balancer = STTLoadBalancer(providers=["azure_whisper", "deepgram"])

        providers = [balancer.select_provider() for _ in range(6)]

        # Should alternate: azure, deepgram, azure, deepgram, azure, deepgram
        assert providers == [
            "azure_whisper",
            "deepgram",
            "azure_whisper",
            "deepgram",
            "azure_whisper",
            "deepgram",
        ]

    def test_single_provider(self):
        """Test behavior with only one provider."""
        balancer = STTLoadBalancer(providers=["deepgram"])

        # Always returns the only provider
        assert balancer.select_provider(chunk_number=0) == "deepgram"
        assert balancer.select_provider(chunk_number=1) == "deepgram"
        assert balancer.select_provider(chunk_number=2) == "deepgram"

    def test_fallback_provider(self):
        """Test fallback when provider fails."""
        balancer = STTLoadBalancer(providers=["azure_whisper", "deepgram"])

        # If azure fails, should fallback to deepgram
        fallback = balancer.get_fallback_provider("azure_whisper")
        assert fallback == "deepgram"

        # If deepgram fails, should fallback to azure
        fallback = balancer.get_fallback_provider("deepgram")
        assert fallback == "azure_whisper"

    def test_no_providers_error(self):
        """Test error when no providers available."""
        with pytest.raises(ValueError, match="No STT providers available"):
            STTLoadBalancer(providers=[])

    def test_stats(self):
        """Test stats reporting."""
        balancer = STTLoadBalancer(providers=["azure_whisper", "deepgram"])

        stats = balancer.get_stats()

        assert stats["num_providers"] == 2
        assert stats["strategy"] == "round_robin"
        assert stats["providers"] == ["azure_whisper", "deepgram"]
