"""
Tests for redaction_style.yaml enforcement
"""

import re
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def redaction_config():
    """Load redaction config."""
    config_path = Path(__file__).parent.parent / "config" / "redaction_style.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def apply_redaction(text: str, config: dict) -> str:
    """Apply redaction patterns from config."""
    result = text

    # Apply regex patterns
    for pattern_name, pattern_config in config["patterns"].items():
        if pattern_config["enabled"]:
            regex = pattern_config["regex"]
            replacement = pattern_config["replacement"]
            result = re.sub(regex, replacement, result)

    # Apply PHI patterns
    if "phi" in config:
        for phi_name, phi_config in config["phi"].items():
            if phi_config["enabled"]:
                regex = phi_config["regex"]
                replacement = phi_config["replacement"]
                result = re.sub(regex, replacement, result)

    return result


class TestRedactionPatterns:
    """Test redaction pattern matching."""

    def test_email_redaction(self, redaction_config) -> None:
        """Test email pattern redaction."""
        text = "Contact me at john.doe@example.com for details."
        redacted = apply_redaction(text, redaction_config)

        assert "john.doe@example.com" not in redacted
        assert "[REDACTED_EMAIL]" in redacted

    def test_phone_redaction(self, redaction_config) -> None:
        """Test phone number redaction."""
        text = "Call me at 555-123-4567 or (555) 987-6543."
        redacted = apply_redaction(text, redaction_config)

        assert "555-123-4567" not in redacted
        assert "[REDACTED_PHONE]" in redacted

    def test_ssn_redaction(self, redaction_config) -> None:
        """Test SSN redaction."""
        text = "Patient SSN: 123-45-6789"
        redacted = apply_redaction(text, redaction_config)

        assert "123-45-6789" not in redacted
        assert "[REDACTED_SSN]" in redacted

    def test_credit_card_redaction(self, redaction_config) -> None:
        """Test credit card redaction."""
        text = "Card: 1234-5678-9012-3456"
        redacted = apply_redaction(text, redaction_config)

        assert "1234-5678-9012-3456" not in redacted
        assert "[REDACTED_CC]" in redacted

    def test_mrn_redaction(self, redaction_config) -> None:
        """Test MRN (Medical Record Number) redaction."""
        text = "Patient MRN: 1234567"
        redacted = apply_redaction(text, redaction_config)

        assert "1234567" not in redacted
        assert "[REDACTED_MRN]" in redacted

    def test_patient_name_redaction(self, redaction_config) -> None:
        """Test patient name redaction."""
        text = "Patient: John Smith was admitted yesterday."
        redacted = apply_redaction(text, redaction_config)

        assert "John Smith" not in redacted
        assert "[REDACTED_NAME]" in redacted

    def test_multiple_patterns(self, redaction_config) -> None:
        """Test multiple redaction patterns in one text."""
        text = """
        Patient: Jane Doe
        MRN: 9876543
        Email: jane.doe@hospital.com
        Phone: (555) 123-4567
        SSN: 987-65-4321
        """
        redacted = apply_redaction(text, redaction_config)

        # Verify all patterns redacted
        assert "Jane Doe" not in redacted
        assert "9876543" not in redacted
        assert "jane.doe@hospital.com" not in redacted
        assert "(555) 123-4567" not in redacted
        assert "987-65-4321" not in redacted

        # Verify replacements present
        assert "[REDACTED_NAME]" in redacted
        assert "[REDACTED_MRN]" in redacted
        assert "[REDACTED_EMAIL]" in redacted
        assert "[REDACTED_PHONE]" in redacted
        assert "[REDACTED_SSN]" in redacted

    def test_preserve_structure(self, redaction_config) -> None:
        """Test that structure is preserved (not just deleted)."""
        text = "Email: admin@example.com"
        redacted = apply_redaction(text, redaction_config)

        # Should keep "Email: " prefix
        assert redacted.startswith("Email: ")
        assert "[REDACTED_EMAIL]" in redacted

    def test_max_preview_chars(self, redaction_config) -> None:
        """Test that preview respects max_preview_chars limit."""
        max_chars = redaction_config.get("max_preview_chars", 60)

        # Long text with PII
        long_text = "This is a very long text " * 10 + " with email test@example.com at the end"
        redacted = apply_redaction(long_text, redaction_config)

        # Verify email is redacted
        assert "test@example.com" not in redacted

        # Create preview (truncate to max_chars)
        preview = redacted[:max_chars] if len(redacted) > max_chars else redacted

        # Verify preview is within limit
        assert len(preview) <= max_chars

    def test_curp_rfc_mexican_ids(self, redaction_config) -> None:
        """Test CURP and RFC (Mexican ID) redaction."""
        text = "CURP: AAAA860101HDFLRL09 RFC: AAAA860101A11"
        redacted = apply_redaction(text, redaction_config)

        # Verify both patterns redacted
        assert "AAAA860101HDFLRL09" not in redacted
        assert "AAAA860101A11" not in redacted
        assert "[REDACTED_CURP]" in redacted
        assert "[REDACTED_RFC]" in redacted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
