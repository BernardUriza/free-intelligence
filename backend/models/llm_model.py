"""LLM Model definitions for AI persona configuration.

Provides data structures for managing available LLM models
that can be assigned to AI personas.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    OLLAMA = "ollama"


class CostTier(str, Enum):
    """Model cost classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LLMModel(BaseModel):
    """LLM Model configuration.

    Represents an AI model that can be used by personas for inference.
    Stored in YAML config for persistence.
    """

    id: str = Field(..., description="Unique model identifier (e.g., 'gpt-4o')")
    label: str = Field(..., description="Display name for UI")
    provider: LLMProvider = Field(..., description="Model provider")
    cost_tier: CostTier = Field(CostTier.MEDIUM, description="Cost classification")
    max_tokens: int = Field(4096, description="Maximum output tokens")
    context_window: int = Field(128000, description="Context window size")
    is_active: bool = Field(True, description="Available for selection")
    description: str | None = Field(None, description="Optional model description")
    size_bytes: int | None = Field(None, description="Model size in bytes (for local models)")
    ram_required_gb: float | None = Field(None, description="Estimated RAM required in GB")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class LLMModelCreate(BaseModel):
    """Request schema for creating a new LLM model."""

    id: str = Field(..., min_length=2, max_length=50)
    label: str = Field(..., min_length=2, max_length=100)
    provider: LLMProvider
    cost_tier: CostTier = CostTier.MEDIUM
    max_tokens: int = Field(4096, ge=1, le=1000000)
    context_window: int = Field(128000, ge=1024, le=2000000)
    is_active: bool = True
    description: str | None = None
    size_bytes: int | None = Field(None, ge=0, description="Model size in bytes")
    ram_required_gb: float | None = Field(None, ge=0, description="Estimated RAM required in GB")

    class Config:
        use_enum_values = True


class LLMModelUpdate(BaseModel):
    """Request schema for updating an LLM model."""

    label: str | None = Field(None, min_length=2, max_length=100)
    provider: LLMProvider | None = None
    cost_tier: CostTier | None = None
    max_tokens: int | None = Field(None, ge=1, le=1000000)
    context_window: int | None = Field(None, ge=1024, le=2000000)
    is_active: bool | None = None
    description: str | None = None
    size_bytes: int | None = Field(None, ge=0, description="Model size in bytes")
    ram_required_gb: float | None = Field(None, ge=0, description="Estimated RAM required in GB")

    class Config:
        use_enum_values = True


class LLMModelResponse(BaseModel):
    """API response schema for LLM model."""

    id: str
    label: str
    provider: str
    cost_tier: str
    max_tokens: int
    context_window: int
    is_active: bool
    description: str | None = None
    size_bytes: int | None = None
    ram_required_gb: float | None = None
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, model: LLMModel) -> LLMModelResponse:
        """Convert LLMModel to API response."""
        return cls(
            id=model.id,
            label=model.label,
            provider=model.provider if isinstance(model.provider, str) else model.provider.value,
            cost_tier=model.cost_tier
            if isinstance(model.cost_tier, str)
            else model.cost_tier.value,
            max_tokens=model.max_tokens,
            context_window=model.context_window,
            is_active=model.is_active,
            description=model.description,
            size_bytes=model.size_bytes,
            ram_required_gb=model.ram_required_gb,
            created_at=model.created_at.isoformat(),
            updated_at=model.updated_at.isoformat(),
        )
