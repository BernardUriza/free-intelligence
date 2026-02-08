"""Centralized Secrets Management with Azure KeyVault + .env fallback.

This module provides a unified way to access secrets across the application.
It tries Azure KeyVault first, then falls back to environment variables.

Phase 2.3 Jupiter: Implements ISecretsManager interface for DI.

Usage (DI - Recommended):
    from backend.infrastructure.config.dependencies import get_secrets_manager_dep

    secrets_manager = get_secrets_manager_dep()
    api_key = secrets_manager.get("OPENAI_API_KEY")

Usage (Legacy - Deprecated):
    from backend.config.secrets import get_secret, secrets

    api_key = get_secret("OPENAI_API_KEY")

Author: Bernard Uriza Orozco
Created: 2025-12-11
Updated: 2026-02-01 (Phase 2.3 Jupiter - ISecretsManager implementation)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import os
from dotenv import load_dotenv

from backend.config.interfaces.isecrets_manager import ISecretsManager

# Load .env file as fallback
load_dotenv()

# Azure KeyVault configuration
KEYVAULT_NAME = os.getenv("AZURE_KEYVAULT_NAME", "aurity-secrets")
KEYVAULT_URL = f"https://{KEYVAULT_NAME}.vault.azure.net/"


def _normalize_secret_name(name: str, for_keyvault: bool = False) -> str:
    """Normalize secret name for KeyVault (uses hyphens) or env vars (uses underscores)."""
    if for_keyvault:
        return name.replace("_", "-")
    return name.replace("-", "_")


class AzureKeyVaultSecretsManager(ISecretsManager):
    """Azure KeyVault secrets manager with environment variable fallback.

    Implements ISecretsManager interface for dependency injection.
    Tries Azure KeyVault first, falls back to environment variables.
    """

    def __init__(self, keyvault_url: str | None = None) -> None:
        """Initialize Azure KeyVault secrets manager.

        Args:
            keyvault_url: KeyVault URL. If None, uses AZURE_KEYVAULT_NAME env var.
        """
        self._keyvault_url = keyvault_url or KEYVAULT_URL
        self._keyvault_client: Any = None
        self._keyvault_available: bool | None = None
        self._cache: dict[str, str | None] = {}

    def _get_keyvault_client(self) -> Any:
        """Get or create Azure KeyVault client (lazy initialization)."""
        if self._keyvault_available is False:
            return None

        if self._keyvault_client is not None:
            return self._keyvault_client

        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            credential = DefaultAzureCredential()
            self._keyvault_client = SecretClient(
                vault_url=self._keyvault_url, credential=credential
            )
            self._keyvault_available = True
            return self._keyvault_client
        except ImportError:
            self._keyvault_available = False
            return None
        except Exception:
            self._keyvault_available = False
            return None

    def get(self, name: str, default: str | None = None) -> str | None:
        """Get a secret from KeyVault with .env fallback.

        Args:
            name: Secret name (can use underscores or hyphens)
            default: Default value if secret not found

        Returns:
            Secret value or default
        """
        # Check cache first
        cache_key = f"{name}:{default}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try Azure KeyVault first
        client = self._get_keyvault_client()
        if client:
            try:
                keyvault_name = _normalize_secret_name(name, for_keyvault=True)
                secret = client.get_secret(keyvault_name)
                value = secret.value
                self._cache[cache_key] = value
                return value
            except Exception:
                pass

        # Fallback to environment variable
        env_name = _normalize_secret_name(name, for_keyvault=False)
        value = os.getenv(env_name, default)
        self._cache[cache_key] = value
        return value

    def get_required(self, name: str) -> str:
        """Get a required secret (raises if not found).

        Args:
            name: Secret name

        Returns:
            Secret value

        Raises:
            ValueError: If secret not found in KeyVault or .env
        """
        value = self.get(name)
        if value is None:
            raise ValueError(
                f"Required secret '{name}' not found. "
                f"Set it in Azure KeyVault or .env file."
            )
        return value

    def is_available(self) -> bool:
        """Check if Azure KeyVault is available.

        Returns:
            True if KeyVault client connected successfully
        """
        self._get_keyvault_client()
        return self._keyvault_available is True


class EnvSecretsManager(ISecretsManager):
    """Environment-only secrets manager (for testing/local development).

    Implements ISecretsManager using only environment variables.
    No Azure KeyVault dependency.
    """

    def __init__(self, env_overrides: dict[str, str] | None = None) -> None:
        """Initialize environment secrets manager.

        Args:
            env_overrides: Optional dict of secret overrides (for testing).
        """
        self._overrides = env_overrides or {}

    def get(self, name: str, default: str | None = None) -> str | None:
        """Get a secret from environment or overrides.

        Args:
            name: Secret name
            default: Default value if secret not found

        Returns:
            Secret value or default
        """
        env_name = _normalize_secret_name(name, for_keyvault=False)
        if env_name in self._overrides:
            return self._overrides[env_name]
        return os.getenv(env_name, default)

    def get_required(self, name: str) -> str:
        """Get a required secret (raises if not found).

        Args:
            name: Secret name

        Returns:
            Secret value

        Raises:
            ValueError: If secret not found
        """
        value = self.get(name)
        if value is None:
            raise ValueError(f"Required secret '{name}' not found in environment.")
        return value

    def is_available(self) -> bool:
        """Environment is always available.

        Returns:
            Always True
        """
        return True


# Default secrets manager instance (lazy loaded)
_default_secrets_manager: AzureKeyVaultSecretsManager | None = None


def _get_default_secrets_manager() -> AzureKeyVaultSecretsManager:
    """Get default secrets manager for backwards compatibility."""
    global _default_secrets_manager
    if _default_secrets_manager is None:
        _default_secrets_manager = AzureKeyVaultSecretsManager()
    return _default_secrets_manager


@lru_cache(maxsize=50)
def get_secret(name: str, default: str | None = None) -> str | None:
    """Get a secret from KeyVault with .env fallback.

    Args:
        name: Secret name (can use underscores or hyphens)
        default: Default value if secret not found

    Returns:
        Secret value or default
    """
    return _get_default_secrets_manager().get(name, default)


def get_secret_required(name: str) -> str:
    """Get a required secret (raises if not found).

    Args:
        name: Secret name

    Returns:
        Secret value

    Raises:
        ValueError: If secret not found in KeyVault or .env
    """
    return _get_default_secrets_manager().get_required(name)


class Secrets:
    """Pre-loaded secrets for convenient access.

    Usage:
        from backend.config.secrets import secrets

        key = secrets.AZURE_OPENAI_TTS_API_KEY
    """

    __slots__ = (
        "JWT_SECRET",
        "DATABASE_URL",
        "HF_TOKEN",
    )

    def __init__(
        self,
        *,
        # Auth
        JWT_SECRET: str | None = None,  # noqa: N803
        # Database
        DATABASE_URL: str = "sqlite:///./data/aurity.db",  # noqa: N803
        # Optional services
        HF_TOKEN: str | None = None,  # noqa: N803
    ) -> None:
        self.JWT_SECRET = JWT_SECRET
        self.DATABASE_URL = DATABASE_URL
        self.HF_TOKEN = HF_TOKEN

    @classmethod
    def load(cls) -> Secrets:
        """Load all secrets from KeyVault/.env."""
        return cls(
            # Auth
            JWT_SECRET=get_secret("JWT_SECRET"),
            # Database
            DATABASE_URL=get_secret("DATABASE_URL", "sqlite:///./data/aurity.db"),
            # Optional services
            HF_TOKEN=get_secret("HF_TOKEN"),
        )


# Global secrets instance (lazy loaded)
_secrets_instance: Secrets | None = None


def get_secrets() -> Secrets:
    """Get the global secrets instance."""
    global _secrets_instance
    if _secrets_instance is None:
        _secrets_instance = Secrets.load()
    return _secrets_instance


# Convenience alias (overwritten below by _SecretsProxy)
_secrets_property = property(lambda _: get_secrets())


# For direct import: from backend.config.secrets import secrets
class _SecretsProxy:
    """Proxy that lazily loads secrets on first access."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_secrets(), name)


secrets = _SecretsProxy()


# Quick test when run directly
if __name__ == "__main__":
    print("\n Testing Secrets Manager\n")
    print(f"KeyVault: {KEYVAULT_URL}")

    # Test new DI-compatible class
    manager = AzureKeyVaultSecretsManager()
    print(f"KeyVault Available: {manager.is_available()}")
    print()

    # Test loading via legacy interface
    s = get_secrets()
    print("Loaded secrets:")
    print(f"  JWT_SECRET: {'Set' if s.JWT_SECRET else 'Missing'}")
