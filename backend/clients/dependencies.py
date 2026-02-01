"""FastAPI Dependency Injection providers for Internal LLM Client.

Provides type-safe configuration for HTTP client used by assistant service.

Author: Claude Code
Created: 2026-01-31
Pattern: Type-Safe Config Validation with Pydantic
"""

import os
from typing import TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from backend.clients.internal_llm_client import InternalLLMClient


class LLMClientConfig(BaseModel):
    """Type-safe configuration for InternalLLMClient (HTTP wrapper).

    Validation Rules:
        - base_url: Must be valid HTTP(S) URL
        - timeout_connect: Must be > 0 (seconds)
        - timeout_read: Must be > timeout_connect (LLM inference can take minutes)
        - timeout_write: Must be > 0
        - timeout_pool: Must be > 0
        - enforce_security_guard: Boolean flag

    Immutability:
        - frozen=True prevents accidental modification after initialization
    """

    base_url: str = Field(
        min_length=1,
        default="http://localhost:7001",
        description="Base URL for internal backend API",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Ensure base_url is a valid HTTP(S) URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v
    timeout_connect: float = Field(
        gt=0.0,
        default=10.0,
        description="HTTP connect timeout in seconds",
    )
    timeout_read: float = Field(
        gt=0.0,
        default=180.0,
        description="HTTP read timeout (must handle long LLM inference, 3 min default)",
    )
    timeout_write: float = Field(
        gt=0.0,
        default=10.0,
        description="HTTP write timeout in seconds",
    )
    timeout_pool: float = Field(
        gt=0.0,
        default=10.0,
        description="HTTP connection pool timeout in seconds",
    )
    enforce_security_guard: bool = Field(
        default=False,
        description="Enforce security guard (raise error if public calls internal directly)",
    )

    model_config = ConfigDict(frozen=True)


def get_llm_client_config() -> LLMClientConfig:
    """Get LLM client configuration from environment variables.

    Environment Variables:
        FI_BACKEND_URL=http://localhost:7001 → Base URL
        FI_TIMEOUT_CONNECT=10.0 → Connect timeout (seconds)
        FI_TIMEOUT_READ=180.0 → Read timeout (seconds)
        FI_TIMEOUT_WRITE=10.0 → Write timeout (seconds)
        FI_TIMEOUT_POOL=10.0 → Pool timeout (seconds)
        FI_ENFORCE_GUARD=false → Enforce security guard

    Returns:
        LLMClientConfig instance (immutable, validated)

    Raises:
        ValidationError: If configuration is invalid (e.g., timeout_read <= 0)
    """
    return LLMClientConfig(
        base_url=os.getenv("FI_BACKEND_URL", "http://localhost:7001"),
        timeout_connect=float(os.getenv("FI_TIMEOUT_CONNECT", "10.0")),
        timeout_read=float(os.getenv("FI_TIMEOUT_READ", "180.0")),
        timeout_write=float(os.getenv("FI_TIMEOUT_WRITE", "10.0")),
        timeout_pool=float(os.getenv("FI_TIMEOUT_POOL", "10.0")),
        enforce_security_guard=os.getenv("FI_ENFORCE_GUARD", "false").lower() == "true",
    )


def get_llm_client_dep() -> "InternalLLMClient":
    """Get InternalLLMClient with type-safe configuration (FastAPI Depends).

    This is the dependency injection provider for endpoints.
    Use this with FastAPI Depends() instead of calling get_llm_client() directly.

    Returns:
        InternalLLMClient instance with validated config

    Example:
        @router.post("/endpoint")
        async def endpoint(llm_client: InternalLLMClient = Depends(get_llm_client_dep)):
            result = await llm_client.chat(...)
    """
    # Import here to avoid circular dependency
    from backend.clients.internal_llm_client import InternalLLMClient

    config = get_llm_client_config()
    return InternalLLMClient(config=config)
