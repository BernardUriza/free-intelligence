"""Unit tests for redactor module.

Tests PII/PHI redaction utilities.
"""

from __future__ import annotations

import re

import pytest
from backend.utils.redactor import (
    DEFAULT_REDACT_RULES,
    redact_and_hash_once,
    redact_text,
)


class TestRedactText:
    """Tests for redact_text function."""

    def test_empty_string_returns_empty(self) -> None:
        """Empty string returns empty."""
        assert redact_text("") == ""

    def test_none_returns_none(self) -> None:
        """None returns None (falsy check)."""
        assert redact_text(None) is None  # type: ignore[arg-type]

    def test_default_rules_redact_long_numbers(self) -> None:
        """Default rules redact numbers with 5+ digits."""
        result = redact_text("Mi número es 12345678")
        assert "12345678" not in result
        assert "[REDACTED:" in result

    def test_default_rules_redact_curp(self) -> None:
        """Default rules redact CURP mentions."""
        result = redact_text("Mi CURP es importante")
        assert "CURP" not in result
        assert "[REDACTED:" in result

    def test_default_rules_redact_rfc(self) -> None:
        """Default rules redact RFC mentions."""
        result = redact_text("Mi RFC está registrado")
        assert "RFC" not in result
        assert "[REDACTED:" in result

    def test_case_insensitive_redaction(self) -> None:
        """Redaction is case insensitive."""
        result = redact_text("curp y Curp y CURP")
        assert "curp" not in result.lower().replace("[redacted:", "")

    def test_custom_rules_override_default(self) -> None:
        """Custom rules override default rules."""
        result = redact_text("Mi nombre es Juan", [r"\bJuan\b"])
        assert "Juan" not in result
        assert "[REDACTED:" in result
        # Default rules not applied with custom
        result2 = redact_text("12345678", [r"\bJuan\b"])
        assert "12345678" in result2  # Not redacted with custom rules

    def test_multiple_matches_same_pattern(self) -> None:
        """Multiple matches of same pattern all redacted."""
        result = redact_text("12345 y 67890 y 11111")
        assert "12345" not in result
        assert "67890" not in result
        assert "11111" not in result

    def test_hash_is_deterministic(self) -> None:
        """Same value produces same hash."""
        result1 = redact_text("12345678")
        result2 = redact_text("12345678")
        assert result1 == result2

    def test_different_values_different_hashes(self) -> None:
        """Different values produce different hashes."""
        result1 = redact_text("12345678")
        result2 = redact_text("87654321")
        # Extract hashes
        hash1 = re.search(r"\[REDACTED:([a-f0-9]{8})\]", result1)
        hash2 = re.search(r"\[REDACTED:([a-f0-9]{8})\]", result2)
        assert hash1 and hash2
        assert hash1.group(1) != hash2.group(1)

    def test_short_numbers_not_redacted(self) -> None:
        """Numbers with less than 5 digits not redacted by default."""
        result = redact_text("Tengo 1234 pesos")
        assert "1234" in result

    def test_invalid_regex_skipped(self) -> None:
        """Invalid regex patterns are skipped gracefully."""
        result = redact_text("Some text", [r"[invalid(regex"])
        assert result == "Some text"

    def test_text_without_matches_unchanged(self) -> None:
        """Text without matches returns unchanged."""
        result = redact_text("Hola mundo")
        assert result == "Hola mundo"

    def test_hash_format(self) -> None:
        """Hash format is [REDACTED:8-char-hex]."""
        result = redact_text("12345678")
        match = re.search(r"\[REDACTED:[a-f0-9]{8}\]", result)
        assert match is not None


class TestRedactAndHashOnce:
    """Tests for redact_and_hash_once function."""

    def test_returns_tuple(self) -> None:
        """Returns tuple of (redacted_text, metadata)."""
        result = redact_and_hash_once("test 12345678")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_metadata_contains_length(self) -> None:
        """Metadata contains original text length."""
        original = "test 12345678"
        _, metadata = redact_and_hash_once(original)
        assert metadata["length"] == len(original)

    def test_metadata_contains_hashes(self) -> None:
        """Metadata contains list of found hashes."""
        _, metadata = redact_and_hash_once("12345678 y 87654321")
        assert "hashes" in metadata
        assert isinstance(metadata["hashes"], list)
        assert len(metadata["hashes"]) == 2

    def test_no_matches_empty_hashes(self) -> None:
        """No matches returns empty hashes list."""
        _, metadata = redact_and_hash_once("Hola mundo")
        assert metadata["hashes"] == []

    def test_redacted_text_returned(self) -> None:
        """First element is properly redacted text."""
        redacted, _ = redact_and_hash_once("Mi CURP")
        assert "CURP" not in redacted
        assert "[REDACTED:" in redacted

    def test_custom_rules(self) -> None:
        """Custom rules work with hash collection."""
        redacted, metadata = redact_and_hash_once("email@test.com", [r"\S+@\S+"])
        assert "email@test.com" not in redacted
        assert len(metadata["hashes"]) == 1

    def test_hash_values_match_redacted(self) -> None:
        """Collected hashes match those in redacted text."""
        redacted, metadata = redact_and_hash_once("12345678")
        for h in metadata["hashes"]:
            assert f"[REDACTED:{h}]" in redacted


class TestDefaultRedactRules:
    """Tests for DEFAULT_REDACT_RULES constant."""

    def test_default_rules_exist(self) -> None:
        """Default rules list exists and is not empty."""
        assert DEFAULT_REDACT_RULES
        assert len(DEFAULT_REDACT_RULES) >= 2

    def test_default_rules_are_valid_regex(self) -> None:
        """All default rules are valid regex patterns."""
        for rule in DEFAULT_REDACT_RULES:
            # Should not raise
            re.compile(rule)
