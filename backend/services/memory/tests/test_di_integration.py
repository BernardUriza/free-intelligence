"""Integration tests for DI with MemoryStoreConfig.

Tests config validation flows through DI container correctly.

Author: Claude Code
Created: 2026-01-31
Card: Type-Safe Config Validation Pattern
"""

import pytest
from pydantic import ValidationError
from backend.services.memory.dependencies import get_memory_service, get_memory_config


class TestMemoryServiceDI:
    """Test config flows through DI correctly."""

    def test_get_memory_service_with_valid_env(self, monkeypatch):
        """✅ Service initializes with valid env config."""
        monkeypatch.setenv("USE_ELASTICSEARCH", "false")
        monkeypatch.setenv("MEMORY_CACHE_SIZE", "500")

        # Should not raise ValidationError
        service = get_memory_service()

        assert service is not None
        # Service initialized successfully (config validated)

    def test_invalid_env_config_fails_on_service_init(self, monkeypatch):
        """❌ Invalid config raises ValidationError during service init."""
        monkeypatch.setenv("MEMORY_CACHE_SIZE", "-100")

        with pytest.raises(ValidationError) as exc_info:
            get_memory_service()

        # Verify error is about cache_size validation
        errors = exc_info.value.errors()
        cache_error = [e for e in errors if e["loc"][0] == "cache_size"]
        assert len(cache_error) > 0

    def test_config_validation_before_store_init(self, monkeypatch):
        """✅ Config validated BEFORE store initialization (fail-fast)."""
        # Invalid config should fail at get_memory_config(), not later
        monkeypatch.setenv("MEMORY_CACHE_SIZE", "0")

        with pytest.raises(ValidationError):
            _ = get_memory_config()
            # Should never reach here - ValidationError raised in __init__
