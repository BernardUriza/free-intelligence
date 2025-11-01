#!/usr/bin/env python3
"""
Unit tests for configuration loader.

Tests cover:
1. Valid configuration loading
2. Invalid schema detection
3. Missing file fallback to defaults

FI-CONFIG-FEAT-001
"""

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from config_loader import ConfigValidationError, get_default_config, load_config


class TestConfigLoader(unittest.TestCase):
    """Test suite for YAML configuration loader."""

    def test_valid_config(self) -> None:
        """Test loading a valid configuration file."""
        valid_config = {
            "system": {
                "name": "Free Intelligence",
                "version": "0.1.0",
                "timezone": "America/Mexico_City",
                "log_level": "INFO",
            },
            "storage": {
                "corpus_path": "/tmp/corpus.h5",
                "backup_path": "/tmp/backups",
                "exports_path": "/tmp/exports",
                "max_file_size_gb": 4,
            },
            "server": {"host": "127.0.0.1", "port": 7000, "lan_only": True},
            "models": {
                "default": "claude-3-5-sonnet-20241022",
                "available": ["claude-3-5-sonnet-20241022"],
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_dim": 768,
            },
            "features": {"semantic_search": True, "session_persistence": True},
            "limits": {
                "max_sessions": 1000,
                "max_interactions_per_session": 10000,
                "retention_bundles": 12,
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(valid_config, f)
            temp_path = f.name

        try:
            config = load_config(temp_path)
            self.assertEqual(config["system"]["name"], "Free Intelligence")
            self.assertEqual(config["server"]["port"], 7000)
            self.assertEqual(config["models"]["embedding_dim"], 768)
        finally:
            Path(temp_path).unlink()

    def test_invalid_config_missing_section(self) -> None:
        """Test that missing required section raises error."""
        invalid_config = {
            "system": {"name": "Test", "version": "0.1.0", "timezone": "UTC", "log_level": "INFO"}
            # Missing: storage, server, models, features, limits
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_path = f.name

        try:
            with self.assertRaises(ConfigValidationError) as context:
                load_config(temp_path)
            self.assertIn("Missing required section", str(context.exception))
        finally:
            Path(temp_path).unlink()

    def test_invalid_config_bad_log_level(self) -> None:
        """Test that invalid log level raises error."""
        invalid_config = {
            "system": {
                "name": "Test",
                "version": "0.1.0",
                "timezone": "UTC",
                "log_level": "INVALID_LEVEL",  # Invalid
            },
            "storage": {
                "corpus_path": "/tmp/corpus.h5",
                "backup_path": "/tmp/backups",
                "exports_path": "/tmp/exports",
                "max_file_size_gb": 4,
            },
            "server": {"host": "127.0.0.1", "port": 7000, "lan_only": True},
            "models": {
                "default": "claude-3-5-sonnet-20241022",
                "available": ["claude-3-5-sonnet-20241022"],
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_dim": 768,
            },
            "features": {"semantic_search": True, "session_persistence": True},
            "limits": {
                "max_sessions": 1000,
                "max_interactions_per_session": 10000,
                "retention_bundles": 12,
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_path = f.name

        try:
            with self.assertRaises(ConfigValidationError) as context:
                load_config(temp_path)
            self.assertIn("Invalid log_level", str(context.exception))
        finally:
            Path(temp_path).unlink()

    def test_invalid_config_bad_port(self) -> None:
        """Test that invalid port number raises error."""
        invalid_config = {
            "system": {"name": "Test", "version": "0.1.0", "timezone": "UTC", "log_level": "INFO"},
            "storage": {
                "corpus_path": "/tmp/corpus.h5",
                "backup_path": "/tmp/backups",
                "exports_path": "/tmp/exports",
                "max_file_size_gb": 4,
            },
            "server": {
                "host": "127.0.0.1",
                "port": 99999,  # Invalid port
                "lan_only": True,
            },
            "models": {
                "default": "claude-3-5-sonnet-20241022",
                "available": ["claude-3-5-sonnet-20241022"],
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_dim": 768,
            },
            "features": {"semantic_search": True, "session_persistence": True},
            "limits": {
                "max_sessions": 1000,
                "max_interactions_per_session": 10000,
                "retention_bundles": 12,
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_path = f.name

        try:
            with self.assertRaises(ConfigValidationError) as context:
                load_config(temp_path)
            self.assertIn("Invalid port", str(context.exception))
        finally:
            Path(temp_path).unlink()

    def test_missing_file_returns_defaults(self) -> None:
        """Test that missing config file returns safe defaults."""
        config = load_config("/nonexistent/path/config.yml")

        # Should return defaults
        self.assertEqual(config["system"]["name"], "Free Intelligence")
        self.assertEqual(config["server"]["port"], 7000)
        self.assertTrue(config["server"]["lan_only"])
        self.assertEqual(config["limits"]["retention_bundles"], 12)

    def test_empty_file_raises_error(self) -> None:
        """Test that empty config file raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("")  # Empty file
            temp_path = f.name

        try:
            with self.assertRaises(ConfigValidationError) as context:
                load_config(temp_path)
            self.assertIn("empty", str(context.exception).lower())
        finally:
            Path(temp_path).unlink()

    def test_get_default_config(self) -> None:
        """Test default configuration generation."""
        defaults = get_default_config()

        self.assertIn("system", defaults)
        self.assertIn("storage", defaults)
        self.assertIn("server", defaults)
        self.assertIn("models", defaults)
        self.assertIn("features", defaults)
        self.assertIn("limits", defaults)

        self.assertEqual(defaults["system"]["name"], "Free Intelligence")
        self.assertEqual(defaults["server"]["port"], 7000)


if __name__ == "__main__":
    unittest.main()
