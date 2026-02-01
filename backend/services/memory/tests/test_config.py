"""Unit tests for MemoryStoreConfig validation.

Test Coverage:
    - Valid configs (HDF5, Elasticsearch)
    - Invalid configs (negative values, wrong types, missing URLs)
    - Environment variable parsing
    - Immutability (frozen=True)
    - Cross-field validation

Author: Claude Code
Created: 2026-01-31
Card: Type-Safe Config Validation Pattern
"""

import pytest
from pydantic import ValidationError
from backend.services.memory.dependencies import MemoryStoreConfig, get_memory_config


class TestMemoryStoreConfigValidation:
    """Test Pydantic validation rules."""

    def test_valid_hdf5_config(self):
        """✅ Valid HDF5 config (use_elasticsearch=False)."""
        config = MemoryStoreConfig(
            use_elasticsearch=False,
            elasticsearch_url=None,
            cache_size=1000,
        )
        assert config.cache_size == 1000
        assert config.use_elasticsearch is False
        assert config.elasticsearch_url is None

    def test_valid_elasticsearch_config(self):
        """✅ Valid Elasticsearch config with URL."""
        config = MemoryStoreConfig(
            use_elasticsearch=True,
            elasticsearch_url="http://localhost:9200",
            cache_size=500,
        )
        assert str(config.elasticsearch_url) == "http://localhost:9200/"
        assert config.use_elasticsearch is True
        assert config.cache_size == 500

    def test_valid_elasticsearch_https_url(self):
        """✅ Valid Elasticsearch config with HTTPS URL."""
        config = MemoryStoreConfig(
            use_elasticsearch=True,
            elasticsearch_url="https://es.production.com:9200",
            cache_size=256,
        )
        assert str(config.elasticsearch_url).startswith("https://")

    def test_negative_cache_size_raises(self):
        """❌ cache_size < 0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MemoryStoreConfig(
                use_elasticsearch=False,
                cache_size=-100,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        error = errors[0]
        assert error["loc"] == ("cache_size",)
        assert "greater than 0" in str(error["msg"])

    def test_zero_cache_size_raises(self):
        """❌ cache_size = 0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MemoryStoreConfig(
                use_elasticsearch=False,
                cache_size=0,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        error = errors[0]
        assert error["loc"] == ("cache_size",)
        assert "greater than 0" in str(error["msg"])

    def test_invalid_elasticsearch_url_raises(self):
        """❌ Invalid URL format should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MemoryStoreConfig(
                use_elasticsearch=True,
                elasticsearch_url="not-a-valid-url",
                cache_size=1000,
            )

        errors = exc_info.value.errors()
        assert len(errors) >= 1
        # URL validation error
        url_error = [e for e in errors if e["loc"][0] == "elasticsearch_url"]
        assert len(url_error) > 0

    def test_missing_es_url_when_enabled_raises(self):
        """❌ use_elasticsearch=True but elasticsearch_url=None should raise."""
        with pytest.raises(ValidationError) as exc_info:
            MemoryStoreConfig(
                use_elasticsearch=True,
                elasticsearch_url=None,
                cache_size=1000,
            )

        errors = exc_info.value.errors()
        assert len(errors) >= 1
        # Cross-field validation error
        error = [e for e in errors if "required when use_elasticsearch=True" in str(e["msg"])]
        assert len(error) > 0

    def test_config_defaults(self):
        """✅ Default values work correctly."""
        config = MemoryStoreConfig()

        assert config.use_elasticsearch is False
        assert config.elasticsearch_url is None
        assert config.cache_size == 128

    def test_config_immutable(self):
        """✅ frozen=True prevents field modification."""
        config = MemoryStoreConfig(
            use_elasticsearch=False,
            cache_size=1000,
        )

        # Pydantic v2 raises ValidationError on frozen model mutation
        with pytest.raises(ValidationError):
            config.cache_size = 2000  # Should fail


class TestMemoryStoreConfigFromEnv:
    """Test environment variable parsing."""

    def test_from_env_defaults(self, monkeypatch):
        """✅ Default HDF5 config when env vars not set."""
        monkeypatch.delenv("USE_ELASTICSEARCH", raising=False)
        monkeypatch.delenv("ELASTICSEARCH_URL", raising=False)
        monkeypatch.delenv("MEMORY_CACHE_SIZE", raising=False)

        config = get_memory_config()

        assert config.use_elasticsearch is False
        assert config.elasticsearch_url is None
        assert config.cache_size == 128

    def test_from_env_elasticsearch_enabled(self, monkeypatch):
        """✅ Elasticsearch config from env vars."""
        monkeypatch.setenv("USE_ELASTICSEARCH", "true")
        monkeypatch.setenv("ELASTICSEARCH_URL", "http://es.local:9200")
        monkeypatch.setenv("MEMORY_CACHE_SIZE", "500")

        config = get_memory_config()

        assert config.use_elasticsearch is True
        assert str(config.elasticsearch_url) == "http://es.local:9200/"
        assert config.cache_size == 500

    def test_from_env_elasticsearch_case_insensitive(self, monkeypatch):
        """✅ USE_ELASTICSEARCH accepts TRUE/True/true."""
        monkeypatch.setenv("USE_ELASTICSEARCH", "TRUE")
        monkeypatch.setenv("ELASTICSEARCH_URL", "http://localhost:9200")

        config = get_memory_config()

        assert config.use_elasticsearch is True

    def test_from_env_invalid_cache_size_raises(self, monkeypatch):
        """❌ Invalid cache_size in env should raise ValidationError."""
        monkeypatch.setenv("MEMORY_CACHE_SIZE", "-50")

        with pytest.raises(ValidationError) as exc_info:
            get_memory_config()

        errors = exc_info.value.errors()
        error = [e for e in errors if e["loc"][0] == "cache_size"]
        assert len(error) > 0

    def test_from_env_elasticsearch_without_url_raises(self, monkeypatch):
        """❌ use_elasticsearch=True without URL should raise."""
        monkeypatch.setenv("USE_ELASTICSEARCH", "true")
        monkeypatch.delenv("ELASTICSEARCH_URL", raising=False)

        with pytest.raises(ValidationError) as exc_info:
            get_memory_config()

        errors = exc_info.value.errors()
        # Should fail cross-field validation
        error = [e for e in errors if "required when use_elasticsearch=True" in str(e["msg"])]
        assert len(error) > 0
