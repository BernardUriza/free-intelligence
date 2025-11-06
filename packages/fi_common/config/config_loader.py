#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Configuration Loader

Loads and validates YAML configuration with schema enforcement.
Provides safe defaults if config file is missing.

FI-CONFIG-FEAT-001
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class ConfigSchema:
    """Schema definition for Free Intelligence configuration."""

    REQUIRED_SECTIONS = ["system", "storage", "server", "models", "features", "limits"]

    REQUIRED_KEYS = {
        "system": ["name", "version", "timezone", "log_level"],
        "storage": ["corpus_path", "backup_path", "exports_path", "max_file_size_gb"],
        "server": ["host", "port", "lan_only"],
        "models": ["default", "available", "embedding_model", "embedding_dim"],
        "features": ["semantic_search", "session_persistence"],
        "limits": ["max_sessions", "max_interactions_per_session", "retention_bundles"],
    }

    VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    @classmethod
    def validate(cls, config: dict[str, Any]) -> list[str]:
        """
        Validate configuration against schema.

        Args:
            config: Configuration dictionary to validate

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Check required sections
        for section in cls.REQUIRED_SECTIONS:
            if section not in config:
                errors.append(f"Missing required section: '{section}'")
                continue

            # Check required keys in section
            if section in cls.REQUIRED_KEYS:
                for key in cls.REQUIRED_KEYS[section]:
                    if key not in config[section]:
                        errors.append(f"Missing required key: '{section}.{key}'")

        # Validate specific fields
        if "system" in config:
            log_level = config["system"].get("log_level")
            if log_level and log_level not in cls.VALID_LOG_LEVELS:
                errors.append(
                    f"Invalid log_level: '{log_level}'. Must be one of {cls.VALID_LOG_LEVELS}"
                )

        if "storage" in config:
            max_size = config["storage"].get("max_file_size_gb")
            if max_size is not None and (not isinstance(max_size, (int, float)) or max_size <= 0):
                errors.append(f"Invalid max_file_size_gb: must be positive number, got {max_size}")

        if "server" in config:
            port = config["server"].get("port")
            if port is not None and (not isinstance(port, int) or port < 1 or port > 65535):
                errors.append(f"Invalid port: must be 1-65535, got {port}")

        if "models" in config:
            embedding_dim = config["models"].get("embedding_dim")
            if embedding_dim is not None and (
                not isinstance(embedding_dim, int) or embedding_dim <= 0
            ):
                errors.append(
                    f"Invalid embedding_dim: must be positive integer, got {embedding_dim}"
                )

        return errors


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


def get_default_config() -> dict[str, Any]:
    """
    Get default configuration values.

    Returns:
        Dictionary with safe default configuration

    Notes:
        Used when config.yml is missing or as fallback for missing keys
    """
    return {
        "system": {
            "name": "Free Intelligence",
            "version": "0.1.0",
            "timezone": "America/Mexico_City",
            "log_level": "INFO",
        },
        "storage": {
            "corpus_path": "./storage/corpus.h5",
            "backup_path": "./backups",
            "exports_path": "./exports",
            "max_file_size_gb": 4,
            "auto_backup_hours": 24,
        },
        "server": {"host": "127.0.0.1", "port": 7000, "lan_only": True, "cors_enabled": False},
        "models": {
            "default": "claude-3-5-sonnet-20241022",
            "available": ["claude-3-5-sonnet-20241022"],
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding_dim": 768,
        },
        "features": {
            "semantic_search": True,
            "auto_export": False,
            "session_persistence": True,
            "multi_user": False,
        },
        "limits": {
            "max_sessions": 1000,
            "max_interactions_per_session": 10000,
            "retention_bundles": 12,
        },
    }


def load_config(config_path: Optional[str] = None) -> dict[str, Any]:
    """
    Load and validate YAML configuration.

    Args:
        config_path: Path to config.yml file. If None, uses default location.
                    If file doesn't exist, returns default configuration.

    Returns:
        Validated configuration dictionary

    Raises:
        ConfigValidationError: If configuration is invalid

    Examples:
        >>> config = load_config()
        >>> print(config["system"]["name"])
        Free Intelligence

        >>> config = load_config("/custom/path/config.yml")
        >>> print(config["server"]["port"])
        7000
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "config.yml"
    else:
        config_path = Path(config_path)

    # Return defaults if file doesn't exist
    if not config_path.exists():
        return get_default_config()

    # Load YAML
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Invalid YAML syntax: {e}")
    except Exception as e:
        raise ConfigValidationError(f"Failed to read config file: {e}")

    if config is None:
        raise ConfigValidationError("Config file is empty")

    # Validate schema
    errors = ConfigSchema.validate(config)
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
        raise ConfigValidationError(error_msg)

    return config


def load_llm_config(config_path: Optional[str] = None) -> dict[str, Any]:
    """
    Load LLM configuration from config/llm.yaml.

    Args:
        config_path: Optional path to llm.yaml (defaults to config/llm.yaml)

    Returns:
        LLM configuration dictionary

    Raises:
        FileNotFoundError: If config file not found
        yaml.YAMLError: If YAML parsing fails
    """
    if config_path is None:
        # Try multiple possible locations
        possible_paths = [
            Path("config/llm.yaml"),
            Path(__file__).parent.parent / "config" / "llm.yaml",
        ]

        for p in possible_paths:
            if p.exists():
                config_path = str(p)
                break

        if config_path is None:
            raise FileNotFoundError(
                "LLM config not found. Tried: " + ", ".join(str(p) for p in possible_paths)
            )

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config or {}


if __name__ == "__main__":
    # CLI usage for validation
    import sys

    try:
        config_path = sys.argv[1] if len(sys.argv) > 1 else None
        config = load_config(config_path)
        print("✅ Configuration is valid")
        print(f"\nSystem: {config['system']['name']} v{config['system']['version']}")
        print(f"Server: {config['server']['host']}:{config['server']['port']}")
        print(f"Default model: {config['models']['default']}")
    except ConfigValidationError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
