"""Base configuration classes with type-safe validation.

This module provides reusable config utilities using Pydantic for
type safety and validation. All config classes should inherit from
BaseConfig to ensure consistent validation behavior.

Author: Claude Code
Created: 2026-01-31
Pattern: Type-Safe Config Validation
"""

from pydantic import BaseModel, ConfigDict
import os


class BaseConfig(BaseModel):
    """Base configuration class with common validation utilities.

    Features:
        - Immutable by default (frozen=True)
        - Type-safe field validation via Pydantic
        - Clear error messages on validation failure
        - Extra fields forbidden (strict mode)

    Usage:
        class MyConfig(BaseConfig):
            api_key: str = Field(min_length=32)
            timeout: int = Field(gt=0, default=30)
    """

    model_config = ConfigDict(
        frozen=True,  # Immutable after creation
        validate_assignment=True,  # Validate on field reassignment
        extra="forbid",  # Reject unknown fields
    )

    @classmethod
    def parse_env_int(
        cls, key: str, default: int, min_value: int | None = None
    ) -> int:
        """Parse integer from env var with validation.

        Args:
            key: Environment variable name
            default: Default value if not set
            min_value: Minimum allowed value (optional)

        Returns:
            Parsed integer value

        Raises:
            ValueError: If value invalid or below min_value

        Example:
            cache_size = BaseConfig.parse_env_int("CACHE_SIZE", 128, min_value=1)
        """
        value_str = os.getenv(key, str(default))
        try:
            value = int(value_str)
        except ValueError:
            raise ValueError(f"{key} must be an integer, got: {value_str}")

        if min_value is not None and value < min_value:
            raise ValueError(f"{key} must be >= {min_value}, got: {value}")

        return value

    @classmethod
    def parse_env_bool(cls, key: str, default: bool = False) -> bool:
        """Parse boolean from env var (case-insensitive).

        Args:
            key: Environment variable name
            default: Default value if not set

        Returns:
            Parsed boolean value

        Accepted values:
            - True: "true", "TRUE", "1", "yes", "YES"
            - False: "false", "FALSE", "0", "no", "NO"

        Example:
            debug_mode = BaseConfig.parse_env_bool("DEBUG", False)
        """
        value_str = os.getenv(key, str(default)).lower()
        return value_str in ("true", "1", "yes")
