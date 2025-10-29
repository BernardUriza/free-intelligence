"""
Free Intelligence - LLM Cache Tests

Tests for disk-based cache with TTL validation.

File: tests/test_llm_cache.py
Created: 2025-10-29
Card: FI-CORE-FEAT-001
"""

import time
from unittest.mock import patch

import pytest

from backend.llm_cache import LLMCache


@pytest.fixture
def temp_cache(tmp_path):
    """Create temporary cache directory."""
    cache_dir = tmp_path / "test_cache"
    return LLMCache(cache_dir=str(cache_dir), ttl_minutes=1)


def test_cache_creates_directory(tmp_path):
    """Test cache creates directory if it doesn't exist."""
    cache_dir = tmp_path / "new_cache"
    assert not cache_dir.exists()

    cache = LLMCache(cache_dir=str(cache_dir))
    assert cache_dir.exists()


def test_cache_compute_key(temp_cache):
    """Test cache key computation (SHA-256)."""
    key1 = temp_cache._compute_key(
        provider="ollama",
        model="qwen2:7b",
        prompt="Hello",
        system="",
        params={"temperature": 0.2},
    )

    key2 = temp_cache._compute_key(
        provider="ollama",
        model="qwen2:7b",
        prompt="Hello",
        system="",
        params={"temperature": 0.2},
    )

    # Same inputs -> same key
    assert key1 == key2
    assert len(key1) == 64  # SHA-256 hex string


def test_cache_different_prompts_different_keys(temp_cache):
    """Test different prompts produce different keys."""
    key1 = temp_cache._compute_key("ollama", "qwen2:7b", "Hello")
    key2 = temp_cache._compute_key("ollama", "qwen2:7b", "Goodbye")

    assert key1 != key2


def test_cache_set_and_get(temp_cache):
    """Test cache stores and retrieves entries."""
    response = {"text": "Test response", "usage": {"in": 10, "out": 20}}

    cache_key = temp_cache.set(
        provider="ollama",
        model="qwen2:7b",
        prompt="Test prompt",
        response=response,
    )

    cached = temp_cache.get(
        provider="ollama",
        model="qwen2:7b",
        prompt="Test prompt",
    )

    assert cached is not None
    assert cached["text"] == "Test response"
    assert cached["usage"]["in"] == 10


def test_cache_miss(temp_cache):
    """Test cache returns None for missing entry."""
    cached = temp_cache.get(
        provider="ollama",
        model="qwen2:7b",
        prompt="Nonexistent prompt",
    )

    assert cached is None


def test_cache_ttl_expiration(temp_cache):
    """Test cache respects TTL (simulated time)."""
    response = {"text": "Test response", "usage": {"in": 10, "out": 20}}

    # Set entry
    temp_cache.set(
        provider="ollama",
        model="qwen2:7b",
        prompt="TTL test",
        response=response,
    )

    # Immediate get (should hit)
    cached = temp_cache.get("ollama", "qwen2:7b", "TTL test")
    assert cached is not None

    # Simulate time passing (mock)
    with patch("time.time", return_value=time.time() + 61):  # 61 seconds > 1 minute TTL
        cached = temp_cache.get("ollama", "qwen2:7b", "TTL test")
        assert cached is None  # Expired


def test_cache_clear_expired(temp_cache):
    """Test clear_expired removes only expired entries."""
    response1 = {"text": "Response 1", "usage": {"in": 10, "out": 20}}
    response2 = {"text": "Response 2", "usage": {"in": 15, "out": 25}}

    # Set two entries
    temp_cache.set("ollama", "qwen2:7b", "Prompt 1", response1)

    # Mock time to make first entry old
    with patch("time.time", return_value=time.time() + 61):
        temp_cache.set("ollama", "qwen2:7b", "Prompt 2", response2)

        # Clear expired (first entry should be removed)
        cleared = temp_cache.clear_expired()

    assert cleared == 1

    # Second entry should still be there
    cached = temp_cache.get("ollama", "qwen2:7b", "Prompt 2")
    assert cached is not None


def test_cache_clear_all(temp_cache):
    """Test clear_all removes all entries."""
    response = {"text": "Test", "usage": {"in": 10, "out": 20}}

    temp_cache.set("ollama", "qwen2:7b", "Prompt 1", response)
    temp_cache.set("ollama", "qwen2:7b", "Prompt 2", response)

    cleared = temp_cache.clear_all()
    assert cleared == 2

    # All entries should be gone
    cached = temp_cache.get("ollama", "qwen2:7b", "Prompt 1")
    assert cached is None


def test_cache_get_stats(temp_cache):
    """Test cache statistics."""
    response = {"text": "Test", "usage": {"in": 10, "out": 20}}

    temp_cache.set("ollama", "qwen2:7b", "Prompt 1", response)
    temp_cache.set("ollama", "qwen2:7b", "Prompt 2", response)

    stats = temp_cache.get_stats()

    assert stats["total_entries"] == 2
    assert stats["total_size_bytes"] > 0
    assert "oldest_age_seconds" in stats
    assert "cache_dir" in stats
