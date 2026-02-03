"""FastAPI Dependency Injection providers for Config/Secrets.

Provides singleton ISecretsManager dependency for services.

Author: Claude Code
Created: 2026-02-02 (Phase 2.3 - DI Refactor - Circular Import Fix)
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.config.interfaces.isecrets_manager import ISecretsManager


@lru_cache(maxsize=1)
def _get_keyvault_secrets_manager_singleton() -> "ISecretsManager":
    """Internal singleton factory for Azure KeyVault SecretsManager."""
    from backend.config.secrets import AzureKeyVaultSecretsManager

    return AzureKeyVaultSecretsManager()


@lru_cache(maxsize=1)
def _get_env_secrets_manager_singleton() -> "ISecretsManager":
    """Internal singleton factory for Env-only SecretsManager."""
    from backend.config.secrets import EnvSecretsManager

    return EnvSecretsManager()


def get_secrets_manager_dep(use_keyvault: bool = True) -> "ISecretsManager":
    """Get secrets manager singleton for services - DI factory.

    Phase 2.3 Jupiter: Centralized secrets management.

    Args:
        use_keyvault: If True, use Azure KeyVault with env fallback.
                     If False, use environment variables only.

    Returns:
        ISecretsManager singleton instance

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
        Two separate singletons for keyvault and env-only modes.

    Note:
        Replaces deprecated get_secret() module-level function.
        Services receive this as a constructor parameter.
    """
    if use_keyvault:
        return _get_keyvault_secrets_manager_singleton()
    return _get_env_secrets_manager_singleton()


__all__ = ["get_secrets_manager_dep"]
