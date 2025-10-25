#!/usr/bin/env python3
"""
Unit tests for structured logger.

Tests cover:
1. Logger initialization with defaults
2. Logger with custom log level
3. Timezone-aware timestamps
4. Config integration

FI-CORE-FEAT-002
"""

import unittest
import json
import sys
from pathlib import Path
from io import StringIO
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from logger import get_logger, init_logger_from_config


class TestLogger(unittest.TestCase):
    """Test suite for structured logger."""

    def test_logger_initialization(self):
        """Test basic logger initialization."""
        logger = get_logger(log_level="INFO")
        self.assertIsNotNone(logger)

    def test_logger_with_custom_level(self):
        """Test logger with custom log level."""
        logger = get_logger(log_level="DEBUG")
        self.assertIsNotNone(logger)

    def test_logger_output_format(self):
        """Test that logger outputs JSON with required fields."""
        # Capture stderr
        captured_output = StringIO()
        original_stderr = sys.stderr
        sys.stderr = captured_output

        try:
            logger = get_logger(log_level="INFO")
            logger.info("test_event", key="value")

            output = captured_output.getvalue()

            # Should be valid JSON
            log_line = output.strip().split('\n')[0]
            log_data = json.loads(log_line)

            # Check required fields
            self.assertIn("event", log_data)
            self.assertIn("timestamp", log_data)
            self.assertIn("level", log_data)
            self.assertEqual(log_data["event"], "test_event")
            self.assertEqual(log_data["key"], "value")
            self.assertEqual(log_data["level"], "info")

        finally:
            sys.stderr = original_stderr

    def test_timezone_aware_timestamp(self):
        """Test that timestamps include timezone information."""
        captured_output = StringIO()
        original_stderr = sys.stderr
        sys.stderr = captured_output

        try:
            logger = get_logger(log_level="INFO", timezone="America/Mexico_City")
            logger.info("timezone_test")

            output = captured_output.getvalue()
            log_line = output.strip().split('\n')[0]
            log_data = json.loads(log_line)

            timestamp = log_data["timestamp"]

            # Check ISO format with timezone
            self.assertIn("T", timestamp)  # ISO 8601 format
            self.assertTrue(timestamp.endswith("-06:00") or timestamp.endswith("-05:00"))  # Mexico City offset

        finally:
            sys.stderr = original_stderr

    def test_init_from_config(self):
        """Test logger initialization from config file."""
        logger = init_logger_from_config()
        self.assertIsNotNone(logger)

    def test_multiple_log_levels(self):
        """Test different log levels."""
        captured_output = StringIO()
        original_stderr = sys.stderr
        sys.stderr = captured_output

        try:
            logger = get_logger(log_level="DEBUG")

            logger.debug("debug_msg")
            logger.info("info_msg")
            logger.warning("warning_msg")
            logger.error("error_msg")

            output = captured_output.getvalue()

            # Should have 4 lines (one for each level)
            lines = output.strip().split('\n')
            self.assertEqual(len(lines), 4)

            # Check each level
            for line in lines:
                log_data = json.loads(line)
                self.assertIn("level", log_data)
                self.assertIn(log_data["level"], ["debug", "info", "warning", "error"])

        finally:
            sys.stderr = original_stderr


if __name__ == "__main__":
    unittest.main()
