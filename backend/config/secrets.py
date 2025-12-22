"""Centralized Secrets Management with Azure KeyVault + .env fallback.

This module provides a unified way to access secrets across the application.
It tries Azure KeyVault first, then falls back to environment variables.

Usage:
    from backend.config.secrets import get_secret, secrets

    # Get a single secret
    api_key = get_secret("OPENAI_API_KEY")

    # Access pre-loaded secrets
    openai_key = secrets.OPENAI_API_KEY

Author: Bernard Uriza Orozco
Created: 2025-12-11
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import os
from dotenv import load_dotenv

# Load .env file as fallback
load_dotenv()

# Azure KeyVault configuration
KEYVAULT_NAME = os.getenv("AZURE_KEYVAULT_NAME", "aurity-secrets")
KEYVAULT_URL = f"https://{KEYVAULT_NAME}.vault.azure.net/"

# Cache for KeyVault client
_keyvault_client = None
_keyvault_available = None


def _get_keyvault_client():
    """Get or create Azure KeyVault client (lazy initialization)."""
    global _keyvault_client, _keyvault_available

    if _keyvault_available is False:
        return None

    if _keyvault_client is not None:
        return _keyvault_client

    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        credential = DefaultAzureCredential()
        _keyvault_client = SecretClient(vault_url=KEYVAULT_URL, credential=credential)
        _keyvault_available = True
        print(f"✅ Connected to Azure KeyVault: {KEYVAULT_NAME}")
        return _keyvault_client
    except ImportError:
        print("⚠️ Azure SDK not installed. Using .env fallback only.")
        print("   Install with: pip install azure-identity azure-keyvault-secrets")
        _keyvault_available = False
        return None
    except Exception as e:
        print(f"⚠️ Azure KeyVault unavailable: {e}")
        print("   Falling back to .env file")
        _keyvault_available = False
        return None


def _normalize_secret_name(name: str, for_keyvault: bool = False) -> str:
    """Normalize secret name for KeyVault (uses hyphens) or env vars (uses underscores)."""
    if for_keyvault:
        return name.replace("_", "-")
    return name.replace("-", "_")


@lru_cache(maxsize=50)
def get_secret(name: str, default: str | None = None) -> str | None:
    """Get a secret from KeyVault with .env fallback.

    Args:
        name: Secret name (can use underscores or hyphens)
        default: Default value if secret not found

    Returns:
        Secret value or default

    Example:
        >>> get_secret("OPENAI_API_KEY")  # Works
        >>> get_secret("OPENAI-API-KEY")  # Also works
    """
    # Try Azure KeyVault first
    client = _get_keyvault_client()
    if client:
        try:
            keyvault_name = _normalize_secret_name(name, for_keyvault=True)
            secret = client.get_secret(keyvault_name)
            return secret.value
        except Exception:
            # Secret not in KeyVault, try .env
            pass

    # Fallback to environment variable
    env_name = _normalize_secret_name(name, for_keyvault=False)
    return os.getenv(env_name, default)


def get_secret_required(name: str) -> str:
    """Get a required secret (raises if not found).

    Args:
        name: Secret name

    Returns:
        Secret value

    Raises:
        ValueError: If secret not found in KeyVault or .env
    """
    value = get_secret(name)
    if value is None:
        raise ValueError(
            f"Required secret '{name}' not found. "
            f"Set it in Azure KeyVault ({KEYVAULT_NAME}) or .env file."
        )
    return value


@dataclass
class Secrets:
    """Pre-loaded secrets for convenient access.

    Usage:
        from backend.config.secrets import secrets

        key = secrets.OPENAI_API_KEY
    """

    # OpenAI
    OPENAI_API_KEY: str | None = None
    OPENAI_TTS_MODEL: str = "tts-1-hd"

    # Auth0
    AUTH0_DOMAIN: str | None = None
    AUTH0_CLIENT_ID: str | None = None
    AUTH0_AUDIENCE: str | None = None
    AUTH0_MANAGEMENT_CLIENT_ID: str | None = None
    AUTH0_MANAGEMENT_CLIENT_SECRET: str | None = None

    # Database
    DATABASE_URL: str = "sqlite:///./data/aurity.db"

    # Optional services
    DEEPGRAM_API_KEY: str | None = None
    AZURE_SPEECH_KEY: str | None = None
    AZURE_SPEECH_REGION: str = "westus"
    CLAUDE_API_KEY: str | None = None
    HF_TOKEN: str | None = None

    @classmethod
    def load(cls) -> Secrets:
        """Load all secrets from KeyVault/.env."""
        return cls(
            # OpenAI
            OPENAI_API_KEY=get_secret("OPENAI_API_KEY"),
            OPENAI_TTS_MODEL=get_secret("OPENAI_TTS_MODEL", "tts-1-hd"),
            # Auth0
            AUTH0_DOMAIN=get_secret("AUTH0_DOMAIN"),
            AUTH0_CLIENT_ID=get_secret("AUTH0_CLIENT_ID"),
            AUTH0_AUDIENCE=get_secret("AUTH0_AUDIENCE", "https://app.aurity.io"),
            AUTH0_MANAGEMENT_CLIENT_ID=get_secret("AUTH0_MANAGEMENT_CLIENT_ID"),
            AUTH0_MANAGEMENT_CLIENT_SECRET=get_secret("AUTH0_MANAGEMENT_CLIENT_SECRET"),
            # Database
            DATABASE_URL=get_secret("DATABASE_URL", "sqlite:///./data/aurity.db"),
            # Optional services
            DEEPGRAM_API_KEY=get_secret("DEEPGRAM_API_KEY"),
            AZURE_SPEECH_KEY=get_secret("AZURE_SPEECH_KEY"),
            AZURE_SPEECH_REGION=get_secret("AZURE_SPEECH_REGION", "westus"),
            CLAUDE_API_KEY=get_secret("CLAUDE_API_KEY"),
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

    def __getattr__(self, name: str):
        return getattr(get_secrets(), name)


secrets = _SecretsProxy()


# Quick test when run directly
if __name__ == "__main__":
    print("\n🔐 Testing Secrets Manager\n")
    print(f"KeyVault: {KEYVAULT_URL}")
    print(f"KeyVault Available: {_keyvault_available}")
    print()

    # Test loading
    s = get_secrets()
    print("Loaded secrets:")
    print(f"  OPENAI_API_KEY: {'✅ Set' if s.OPENAI_API_KEY else '❌ Missing'}")
    print(f"  AUTH0_DOMAIN: {s.AUTH0_DOMAIN or '❌ Missing'}")
    print(f"  AUTH0_CLIENT_ID: {'✅ Set' if s.AUTH0_CLIENT_ID else '❌ Missing'}")
    print(f"  DEEPGRAM_API_KEY: {'✅ Set' if s.DEEPGRAM_API_KEY else '⚪ Not configured'}")
