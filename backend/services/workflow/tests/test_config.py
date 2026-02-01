"""Unit tests for WorkflowConfig validation.

Author: Claude Code
Created: 2026-01-31
Pattern: Type-Safe Config Validation
"""

import pytest
from pydantic import ValidationError
from backend.services.workflow.dependencies import WorkflowConfig, get_workflow_config


class TestWorkflowConfigValidation:
    """Test Pydantic validation rules."""

    def test_valid_default_config(self):
        """✅ Valid config with defaults."""
        config = WorkflowConfig()

        assert config.max_retries == 3
        assert config.timeout_seconds == 300
        assert config.triage_data_dir == "./data/triage_buffers"
        assert config.enable_monitoring is True
        assert config.enable_audit_trail is True
        assert config.max_concurrent_workflows == 10

    def test_max_retries_out_of_range_raises(self):
        """❌ max_retries > 10 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig(max_retries=15)

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("max_retries",)

    def test_negative_timeout_raises(self):
        """❌ Negative timeout should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig(timeout_seconds=-10)

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("timeout_seconds",)

    def test_suspicious_path_raises(self):
        """❌ Suspicious triage_data_dir should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig(triage_data_dir="/etc/passwd")

        errors = exc_info.value.errors()
        error = [e for e in errors if "suspicious path" in str(e["msg"])]
        assert len(error) > 0

    def test_config_immutable(self):
        """✅ frozen=True prevents field modification."""
        config = WorkflowConfig()

        with pytest.raises(ValidationError):
            config.max_retries = 99


class TestWorkflowConfigFromEnv:
    """Test environment variable parsing."""

    def test_from_env_defaults(self, monkeypatch):
        """✅ Default config when env vars not set."""
        monkeypatch.delenv("MAX_RETRIES", raising=False)
        monkeypatch.delenv("WORKFLOW_TIMEOUT", raising=False)

        config = get_workflow_config()

        assert config.max_retries == 3
        assert config.timeout_seconds == 300

    def test_from_env_custom_values(self, monkeypatch):
        """✅ Config from env vars."""
        monkeypatch.setenv("MAX_RETRIES", "5")
        monkeypatch.setenv("WORKFLOW_TIMEOUT", "600")
        monkeypatch.setenv("TRIAGE_DATA_DIR", "./custom/path")
        monkeypatch.setenv("ENABLE_MONITORING", "false")

        config = get_workflow_config()

        assert config.max_retries == 5
        assert config.timeout_seconds == 600
        assert config.triage_data_dir == "./custom/path"
        assert config.enable_monitoring is False

    def test_from_env_invalid_raises(self, monkeypatch):
        """❌ Invalid env value should raise ValidationError."""
        monkeypatch.setenv("MAX_RETRIES", "20")  # > 10

        with pytest.raises(ValidationError) as exc_info:
            get_workflow_config()

        errors = exc_info.value.errors()
        error = [e for e in errors if e["loc"][0] == "max_retries"]
        assert len(error) > 0
