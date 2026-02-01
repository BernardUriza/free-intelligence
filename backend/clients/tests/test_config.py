"""Unit tests for LLMClientConfig validation.

Author: Claude Code
Created: 2026-01-31
Pattern: Type-Safe Config Validation
"""

import pytest
from pydantic import ValidationError
from backend.clients.dependencies import LLMClientConfig, get_llm_client_config


class TestLLMClientConfigValidation:
    """Test Pydantic validation rules."""

    def test_valid_default_config(self):
        """✅ Valid config with defaults."""
        config = LLMClientConfig()

        assert config.base_url == "http://localhost:7001"
        assert config.timeout_connect == 10.0
        assert config.timeout_read == 180.0
        assert config.timeout_write == 10.0
        assert config.timeout_pool == 10.0
        assert config.enforce_security_guard is False

    def test_valid_custom_config(self):
        """✅ Valid config with custom values."""
        config = LLMClientConfig(
            base_url="https://api.example.com",
            timeout_connect=5.0,
            timeout_read=300.0,
            timeout_write=15.0,
            timeout_pool=20.0,
            enforce_security_guard=True,
        )

        assert config.base_url == "https://api.example.com"
        assert config.timeout_connect == 5.0
        assert config.timeout_read == 300.0
        assert config.enforce_security_guard is True

    def test_invalid_base_url_no_protocol(self):
        """❌ base_url without http(s):// should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LLMClientConfig(base_url="localhost:7001")

        errors = exc_info.value.errors()
        error = [e for e in errors if "http" in str(e["msg"]).lower()]
        assert len(error) > 0

    def test_invalid_base_url_empty(self):
        """❌ Empty base_url should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LLMClientConfig(base_url="")

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("base_url",)

    def test_negative_timeout_connect_raises(self):
        """❌ Negative timeout_connect should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LLMClientConfig(timeout_connect=-5.0)

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("timeout_connect",)
        assert "greater than 0" in str(error["msg"])

    def test_zero_timeout_read_raises(self):
        """❌ Zero timeout_read should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LLMClientConfig(timeout_read=0.0)

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("timeout_read",)

    def test_negative_timeout_write_raises(self):
        """❌ Negative timeout_write should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LLMClientConfig(timeout_write=-1.0)

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("timeout_write",)

    def test_negative_timeout_pool_raises(self):
        """❌ Negative timeout_pool should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LLMClientConfig(timeout_pool=-10.0)

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("timeout_pool",)

    def test_config_immutable(self):
        """✅ frozen=True prevents field modification."""
        config = LLMClientConfig()

        with pytest.raises(ValidationError):
            config.timeout_read = 999.0


class TestLLMClientConfigFromEnv:
    """Test environment variable parsing."""

    def test_from_env_defaults(self, monkeypatch):
        """✅ Default config when env vars not set."""
        monkeypatch.delenv("FI_BACKEND_URL", raising=False)
        monkeypatch.delenv("FI_TIMEOUT_READ", raising=False)

        config = get_llm_client_config()

        assert config.base_url == "http://localhost:7001"
        assert config.timeout_read == 180.0

    def test_from_env_custom_values(self, monkeypatch):
        """✅ Config from env vars."""
        monkeypatch.setenv("FI_BACKEND_URL", "https://prod.aurity.io")
        monkeypatch.setenv("FI_TIMEOUT_CONNECT", "15.0")
        monkeypatch.setenv("FI_TIMEOUT_READ", "300.0")
        monkeypatch.setenv("FI_TIMEOUT_WRITE", "20.0")
        monkeypatch.setenv("FI_TIMEOUT_POOL", "25.0")
        monkeypatch.setenv("FI_ENFORCE_GUARD", "true")

        config = get_llm_client_config()

        assert config.base_url == "https://prod.aurity.io"
        assert config.timeout_connect == 15.0
        assert config.timeout_read == 300.0
        assert config.timeout_write == 20.0
        assert config.timeout_pool == 25.0
        assert config.enforce_security_guard is True

    def test_from_env_invalid_raises(self, monkeypatch):
        """❌ Invalid env value should raise ValidationError."""
        monkeypatch.setenv("FI_TIMEOUT_READ", "-100.0")  # Negative timeout

        with pytest.raises(ValidationError) as exc_info:
            get_llm_client_config()

        errors = exc_info.value.errors()
        error = [e for e in errors if e["loc"][0] == "timeout_read"]
        assert len(error) > 0
