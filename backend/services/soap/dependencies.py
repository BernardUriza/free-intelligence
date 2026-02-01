"""FastAPI Dependency Injection providers for SOAP service.

Provides dependency injection for routers using FastAPI Depends().
Direct repository instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Updated: 2026-01-31 (Type-safe config validation with Pydantic)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

from backend.repositories.interfaces import ITaskRepository
from backend.repositories.task_repository import HDF5TaskRepository
from backend.services.soap.services.soap_generation_service import SOAPGenerationService
from backend.config import CORPUS_PATH


class SOAPConfig(BaseModel):
    """Type-safe SOAP generation configuration with validation.

    Validation Rules:
        - llm_provider: Must be one of: claude, ollama, openai, gpt4all
        - max_tokens: Must be between 100 and 16000
        - temperature: Must be between 0.0 and 2.0
        - enable_streaming: Boolean flag
        - timeout_seconds: Must be > 0

    Immutability:
        - frozen=True prevents accidental modification after initialization
    """

    llm_provider: str = Field(
        default="claude",
        description="LLM provider (claude, ollama, openai, gpt4all)",
        pattern="^(claude|ollama|openai|gpt4all)$",
    )
    model_name: str = Field(
        min_length=1,
        default="claude-3-5-sonnet-20241022",
        description="LLM model name",
    )
    max_tokens: int = Field(
        ge=100,
        le=16000,
        default=4000,
        description="Maximum tokens for LLM generation",
    )
    temperature: float = Field(
        ge=0.0,
        le=2.0,
        default=0.7,
        description="LLM temperature (0.0 = deterministic, 2.0 = creative)",
    )
    enable_streaming: bool = Field(
        default=True,
        description="Enable streaming responses for better UX",
    )
    timeout_seconds: int = Field(
        gt=0,
        default=60,
        description="LLM request timeout in seconds",
    )
    enable_validation: bool = Field(
        default=True,
        description="Enable SOAP note validation after generation",
    )
    min_completeness_score: float = Field(
        ge=0.0,
        le=1.0,
        default=0.7,
        description="Minimum completeness score (0.0-1.0) for valid SOAP notes",
    )

    model_config = ConfigDict(frozen=True)


def get_soap_config() -> SOAPConfig:
    """Get SOAP configuration from environment variables.

    Environment Variables:
        LLM_PROVIDER=claude → LLM provider
        LLM_MODEL=claude-3-5-sonnet-20241022 → Model name
        MAX_TOKENS=4000 → Maximum tokens
        LLM_TEMPERATURE=0.7 → Temperature
        ENABLE_STREAMING=true → Enable streaming
        LLM_TIMEOUT=60 → Timeout in seconds
        ENABLE_SOAP_VALIDATION=true → Enable validation
        MIN_COMPLETENESS_SCORE=0.7 → Minimum completeness

    Returns:
        SOAPConfig instance (immutable, validated)

    Raises:
        ValidationError: If configuration is invalid (e.g., temperature > 2.0)
    """
    return SOAPConfig(
        llm_provider=os.getenv("LLM_PROVIDER", "claude"),
        model_name=os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022"),
        max_tokens=int(os.getenv("MAX_TOKENS", "4000")),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        enable_streaming=os.getenv("ENABLE_STREAMING", "true").lower() == "true",
        timeout_seconds=int(os.getenv("LLM_TIMEOUT", "60")),
        enable_validation=os.getenv("ENABLE_SOAP_VALIDATION", "true").lower() == "true",
        min_completeness_score=float(os.getenv("MIN_COMPLETENESS_SCORE", "0.7")),
    )


def get_soap_service() -> SOAPGenerationService:
    """Get SOAP generation service with type-safe configuration.

    Returns:
        SOAPGenerationService instance with validated config

    Note:
        Config validated via Pydantic (fail-fast on invalid values like temperature > 2.0).
    """
    config = get_soap_config()
    return SOAPGenerationService(
        h5_path=str(CORPUS_PATH),
        provider=config.llm_provider,
    )


def get_task_repository() -> ITaskRepository:
    """Get task repository - direct instantiation (Phase 4A).

    Returns:
        ITaskRepository instance (HDF5TaskRepository)

    Note:
        No longer uses service locator (get_container).
        Direct instantiation enables better testability and explicit dependencies.
    """
    return HDF5TaskRepository(CORPUS_PATH)
