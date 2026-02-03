"""Personas Admin Models - Pydantic schemas for persona management.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# Request Schemas
# ============================================================================


class PersonaExample(BaseModel):
    """Few-shot example for persona."""

    input: str = Field(..., description="Example input")
    output: str | dict[str, Any] = Field(..., description="Example output")


class PersonaUpdateRequest(BaseModel):
    """Request to update persona configuration."""

    name: str | None = Field(None, description="Display name")
    description: str | None = Field(None, description="Persona description")
    system_prompt: str | None = Field(None, description="System prompt")
    model: str | None = Field(None, description="LLM model")
    voice: str | None = Field(
        None, description="TTS voice (nova, shimmer, alloy, echo, fable, onyx)"
    )
    temperature: float | None = Field(None, ge=0.0, le=1.0, description="Temperature")
    max_tokens: int | None = Field(None, gt=0, description="Max tokens")
    examples: list[dict[str, Any]] | None = Field(None, description="Few-shot examples")


class PersonaTestRequest(BaseModel):
    """Request to test a persona."""

    input: str = Field(..., description="Test input")
    compare_with_version: int | None = Field(None, description="Compare with version number")


class PersonaCreateRequest(BaseModel):
    """Request to create a new persona (FI-superadmin only)."""

    id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Unique persona ID (lowercase, underscores allowed, e.g., 'my_persona')",
    )
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    description: str = Field(..., min_length=10, description="Persona description (min 10 chars)")
    system_prompt: str = Field(..., min_length=20, description="System prompt (min 20 chars)")
    model: str = Field(default="qwen3:1.7b", description="LLM model ID")
    voice: str | None = Field(default="nova", description="TTS voice")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Temperature (0.0-1.0)")
    max_tokens: int = Field(default=2048, gt=0, le=8192, description="Max tokens (1-8192)")
    examples: list[dict[str, Any]] = Field(default_factory=list, description="Few-shot examples")


# ============================================================================
# Response Schemas
# ============================================================================


class PersonaUsageStats(BaseModel):
    """Usage statistics for a persona."""

    total_invocations: int = Field(default=0, description="Total times invoked")
    avg_latency_ms: float = Field(default=0.0, description="Average latency in ms")
    avg_cost_usd: float = Field(default=0.0, description="Average cost per invocation")


class PersonaResponse(BaseModel):
    """Persona configuration response."""

    id: str = Field(..., description="Persona ID (e.g., 'soap_editor')")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Persona description")
    system_prompt: str = Field(..., description="System prompt")
    model: str = Field(..., description="LLM model (e.g., 'gpt-4o-mini')")
    voice: str | None = Field(None, description="TTS voice (e.g., 'nova', 'shimmer')")
    temperature: float = Field(..., description="Temperature (0.0-1.0)")
    max_tokens: int = Field(..., description="Max tokens")
    examples: list[dict[str, Any]] = Field(default_factory=list, description="Few-shot examples")
    usage_stats: PersonaUsageStats = Field(
        default_factory=PersonaUsageStats, description="Usage statistics"
    )
    version: int = Field(default=1, description="Version number")
    last_updated: str = Field(..., description="Last update timestamp")
    updated_by: str = Field(default="System", description="Last updated by")


class PersonaListResponse(BaseModel):
    """List of personas response."""

    personas: list[PersonaResponse] = Field(..., description="List of personas")


class PersonaTestResponse(BaseModel):
    """Response from persona test."""

    output: str | dict[str, Any] = Field(..., description="LLM output")
    latency_ms: float = Field(..., description="Latency in milliseconds")
    tokens_used: int = Field(default=0, description="Tokens consumed")
    cost_usd: float = Field(default=0.0, description="Estimated cost")
