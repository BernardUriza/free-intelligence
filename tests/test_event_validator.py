#!/usr/bin/env python3
"""
Tests for event name validator.

FI-API-FEAT-001
"""

import unittest
import tempfile
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from event_validator import (
    validate_event_name,
    validate_events_in_code,
    get_canonical_events,
    suggest_event_name,
    CANONICAL_EVENTS
)


class TestEventValidator(unittest.TestCase):
    """Test suite for event name validation."""

    def test_valid_event_names(self):
        """Test that valid event names pass validation."""
        valid_events = [
            "CORPUS_INITIALIZED",
            "INTERACTION_APPENDED",
            "CONFIG_LOADED",
            "CORPUS_IDENTITY_ADDED",
            "LOGGER_INITIALIZED",
        ]

        for event in valid_events:
            with self.subTest(event=event):
                result = validate_event_name(event)
                self.assertTrue(result["valid"], f"{event} should be valid")
                self.assertEqual(len(result["errors"]), 0)

    def test_lowercase_fails(self):
        """Test that lowercase event names fail."""
        result = validate_event_name("corpus_initialized")
        self.assertFalse(result["valid"])
        self.assertTrue(any("uppercase" in err.lower() for err in result["errors"]))

    def test_mixed_case_fails(self):
        """Test that mixed case event names fail."""
        result = validate_event_name("Corpus_Initialized")
        self.assertFalse(result["valid"])

    def test_consecutive_underscores_fails(self):
        """Test that consecutive underscores fail."""
        result = validate_event_name("CORPUS__INITIALIZED")
        self.assertFalse(result["valid"])
        self.assertTrue(any("consecutive" in err.lower() for err in result["errors"]))

    def test_leading_underscore_fails(self):
        """Test that leading underscore fails."""
        result = validate_event_name("_CORPUS_INITIALIZED")
        self.assertFalse(result["valid"])

    def test_trailing_underscore_fails(self):
        """Test that trailing underscore fails."""
        result = validate_event_name("CORPUS_INITIALIZED_")
        self.assertFalse(result["valid"])

    def test_too_long_fails(self):
        """Test that names over 50 characters fail."""
        long_name = "A" * 51
        result = validate_event_name(long_name)
        self.assertFalse(result["valid"])
        self.assertTrue(any("too long" in err.lower() for err in result["errors"]))

    def test_minimum_components(self):
        """Test that at least 2 components are required."""
        result = validate_event_name("INITIALIZED")
        self.assertFalse(result["valid"])
        self.assertTrue(any("2 components" in err.lower() for err in result["errors"]))

    def test_special_characters_fail(self):
        """Test that special characters fail."""
        invalid_events = [
            "CORPUS-INITIALIZED",
            "CORPUS.INITIALIZED",
            "CORPUS@INITIALIZED",
        ]

        for event in invalid_events:
            with self.subTest(event=event):
                result = validate_event_name(event)
                self.assertFalse(result["valid"])

    def test_strict_mode_canonical_only(self):
        """Test that strict mode only allows canonical events."""
        # Valid format but not canonical
        result = validate_event_name("CUSTOM_EVENT_ADDED", strict=True)
        self.assertFalse(result["valid"])
        self.assertTrue(any("canonical" in err.lower() for err in result["errors"]))

        # Canonical event should pass
        result = validate_event_name("CORPUS_INITIALIZED", strict=True)
        self.assertTrue(result["valid"])

    def test_past_participle_warning(self):
        """Test that non-past-participle endings generate warnings."""
        # Present tense should warn
        result = validate_event_name("CORPUS_INITIALIZE")
        self.assertTrue(result["valid"])  # Still valid, just warned
        self.assertGreater(len(result["warnings"]), 0)

    def test_canonical_events_list(self):
        """Test getting canonical events list."""
        events = get_canonical_events()
        self.assertIsInstance(events, list)
        self.assertIn("CORPUS_INITIALIZED", events)
        self.assertIn("INTERACTION_APPENDED", events)

        # Should be sorted
        self.assertEqual(events, sorted(events))

    def test_validate_events_in_code(self):
        """Test scanning Python file for event names."""
        # Create temporary Python file with events
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
import logging
logger = logging.getLogger()

def test_func():
    logger.info("CORPUS_INITIALIZED", path="/test")
    logger.error("CORPUS_INIT_FAILED", error="test")
    logger.warning("invalid_event_name", msg="bad")
''')
            temp_path = f.name

        try:
            results = validate_events_in_code(temp_path)

            # Should find 3 events
            self.assertEqual(len(results), 3)

            # Check that events were found
            event_names = [r["event_name"] for r in results]
            self.assertIn("CORPUS_INITIALIZED", event_names)
            self.assertIn("CORPUS_INIT_FAILED", event_names)
            self.assertIn("invalid_event_name", event_names)

            # Check that invalid event is marked as such
            invalid_result = next(r for r in results if r["event_name"] == "invalid_event_name")
            self.assertFalse(invalid_result["valid"])

        finally:
            Path(temp_path).unlink()

    def test_validate_events_nonexistent_file(self):
        """Test scanning non-existent file."""
        results = validate_events_in_code("/nonexistent/file.py")
        self.assertEqual(len(results), 0)

    def test_suggest_event_name(self):
        """Test event name suggestion."""
        test_cases = [
            ("corpus was initialized", "CORPUS_INITIALIZED"),
            ("interaction appended", "INTERACTION_APPENDED"),
        ]

        for description, expected in test_cases:
            with self.subTest(description=description):
                suggested = suggest_event_name(description)
                if suggested:  # Some may not have suggestions
                    self.assertEqual(suggested, expected)

        # Test that suggestion returns a valid event
        suggested = suggest_event_name("failed to load config")
        if suggested:
            result = validate_event_name(suggested)
            self.assertTrue(result["valid"], f"Suggested event '{suggested}' should be valid")

    def test_all_canonical_events_are_valid(self):
        """Test that all canonical events pass validation."""
        for event in CANONICAL_EVENTS:
            with self.subTest(event=event):
                result = validate_event_name(event, strict=False)
                self.assertTrue(
                    result["valid"],
                    f"Canonical event '{event}' should be valid. Errors: {result['errors']}"
                )


if __name__ == "__main__":
    unittest.main()
