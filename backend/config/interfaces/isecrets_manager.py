"""Secrets Manager Interface.

Defines the contract for secrets management implementations.
Supports Azure KeyVault, environment variables, or any other secret store.

Pattern: Interface Segregation Principle (ISP)
Card: Backend Refactor Phase 2.3 - Jupiter (Secrets DI)
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ISecretsManager(ABC):
    """Interface for secrets management.

    Implementations:
    - AzureKeyVaultSecretsManager: Azure KeyVault with env fallback
    - EnvSecretsManager: Pure environment variables (for testing)

    Usage:
        from backend.infrastructure.config.dependencies import get_secrets_manager_dep

        secrets_manager = get_secrets_manager_dep()
        api_key = secrets_manager.get("OPENAI_API_KEY")
    """

    @abstractmethod
    def get(self, name: str, default: str | None = None) -> str | None:
        """Get a secret by name.

        Args:
            name: Secret name (normalized internally for KeyVault/env)
            default: Default value if secret not found

        Returns:
            Secret value or default
        """
        pass

    @abstractmethod
    def get_required(self, name: str) -> str:
        """Get a required secret (raises if not found).

        Args:
            name: Secret name

        Returns:
            Secret value

        Raises:
            ValueError: If secret not found
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the secrets backend is available.

        Returns:
            True if the secrets store is accessible
        """
        pass
