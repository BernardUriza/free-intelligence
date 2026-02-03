"""Provider Models - Pydantic schemas for provider management.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
Card: FI-DATA-DB-001
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Request Schemas
# ============================================================================


class ProviderCreate(BaseModel):
    """Schema for creating a new provider."""

    nombre: str = Field(..., min_length=1, max_length=100, description="Full name")
    cedula_profesional: str | None = Field(
        None, min_length=1, max_length=20, description="Professional license number"
    )
    especialidad: str | None = Field(None, max_length=100, description="Medical specialty")


class ProviderUpdate(BaseModel):
    """Schema for updating provider data."""

    nombre: str | None = Field(None, min_length=1, max_length=100)
    cedula_profesional: str | None = Field(None, min_length=1, max_length=20)
    especialidad: str | None = Field(None, max_length=100)


# ============================================================================
# Response Schemas
# ============================================================================


class ProviderResponse(BaseModel):
    """Schema for provider API responses."""

    provider_id: str
    nombre: str
    cedula_profesional: str | None
    especialidad: str | None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)
