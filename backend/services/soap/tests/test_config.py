"""Unit tests for SOAPConfig validation.

Author: Claude Code
Created: 2026-01-31
Pattern: Type-Safe Config Validation
"""

import pytest
from pydantic import ValidationError
from backend.services.soap.dependencies import SOAPConfig, get_soap_config


class TestSOAPConfigValidation:
    """Test Pydantic validation rules."""

    def test_valid_default_config(self):
        """✅ Valid config with defaults."""
        config = SOAPConfig()

        assert config.llm_provider == "claude"
        assert config.model_name == "claude-3-5-sonnet-20241022"
        assert config.max_tokens == 4000
        assert config.temperature == 0.7
        assert config.enable_streaming is True
        assert config.timeout_seconds == 60
        assert config.min_completeness_score == 0.7

    def test_valid_custom_config(self):
        """✅ Valid config with custom values."""
        config = SOAPConfig(
            llm_provider="ollama",
            model_name="llama3.1:8b",
            max_tokens=2000,
            temperature=0.3,
            enable_streaming=False,
            timeout_seconds=120,
        )

        assert config.llm_provider == "ollama"
        assert config.temperature == 0.3

    def test_invalid_provider_raises(self):
        """❌ Invalid LLM provider should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SOAPConfig(llm_provider="invalid_provider")

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("llm_provider",)

    def test_max_tokens_out_of_range_raises(self):
        """❌ max_tokens > 16000 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SOAPConfig(max_tokens=20000)

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("max_tokens",)

    def test_temperature_too_high_raises(self):
        """❌ temperature > 2.0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SOAPConfig(temperature=3.5)

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("temperature",)

    def test_negative_timeout_raises(self):
        """❌ Negative timeout should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SOAPConfig(timeout_seconds=-10)

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("timeout_seconds",)

    def test_completeness_score_out_of_range_raises(self):
        """❌ min_completeness_score > 1.0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SOAPConfig(min_completeness_score=1.5)

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("min_completeness_score",)

    def test_config_immutable(self):
        """✅ frozen=True prevents field modification."""
        config = SOAPConfig()

        with pytest.raises(ValidationError):
            config.temperature = 0.9


class TestSOAPConfigFromEnv:
    """Test environment variable parsing."""

    def test_from_env_defaults(self, monkeypatch):
        """✅ Default config when env vars not set."""
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("MAX_TOKENS", raising=False)

        config = get_soap_config()

        assert config.llm_provider == "claude"
        assert config.max_tokens == 4000

    def test_from_env_custom_values(self, monkeypatch):
        """✅ Config from env vars."""
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.setenv("LLM_MODEL", "llama3.1:8b")
        monkeypatch.setenv("MAX_TOKENS", "2000")
        monkeypatch.setenv("LLM_TEMPERATURE", "0.3")
        monkeypatch.setenv("ENABLE_STREAMING", "false")

        config = get_soap_config()

        assert config.llm_provider == "ollama"
        assert config.model_name == "llama3.1:8b"
        assert config.max_tokens == 2000
        assert config.temperature == 0.3
        assert config.enable_streaming is False

    def test_from_env_invalid_raises(self, monkeypatch):
        """❌ Invalid env value should raise ValidationError."""
        monkeypatch.setenv("LLM_TEMPERATURE", "5.0")  # > 2.0

        with pytest.raises(ValidationError) as exc_info:
            get_soap_config()

        errors = exc_info.value.errors()
        error = [e for e in errors if e["loc"][0] == "temperature"]
        assert len(error) > 0
