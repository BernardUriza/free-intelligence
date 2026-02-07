"""Patient Models - Pydantic schemas for patient management.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
Card: FI-DATA-DB-001
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Enums
# =============================================================================


class GenderEnum(str, Enum):
    """Patient gender options - matches database enum."""

    MASCULINO = "MASCULINO"
    FEMENINO = "FEMENINO"
    OTRO = "OTRO"
    NO_ESPECIFICADO = "NO_ESPECIFICADO"


# =============================================================================
# Request Schemas
# =============================================================================


class PatientCreate(BaseModel):
    """Schema for creating a new patient."""

    nombre: str = Field(..., min_length=1, max_length=100, description="First name(s)")
    apellido: str = Field(..., min_length=1, max_length=100, description="Last name(s)")
    fecha_nacimiento: datetime = Field(..., description="Date of birth (ISO 8601)")
    genero: GenderEnum | None = Field(
        None, description="Gender (MASCULINO, FEMENINO, OTRO, NO_ESPECIFICADO)"
    )
    curp: str | None = Field(None, min_length=18, max_length=18, description="CURP (18 chars)")


class PatientUpdate(BaseModel):
    """Schema for updating patient data."""

    nombre: str | None = Field(None, min_length=1, max_length=100)
    apellido: str | None = Field(None, min_length=1, max_length=100)
    fecha_nacimiento: datetime | None = None
    genero: GenderEnum | None = None
    curp: str | None = Field(None, min_length=18, max_length=18)


class CurpValidationRequest(BaseModel):
    """Schema for CURP validation request."""

    curp: str = Field(..., min_length=18, max_length=18, description="CURP to validate")
    exclude_patient_id: str | None = Field(
        None, description="Patient ID to exclude (for updates)"
    )


# =============================================================================
# Response Schemas
# =============================================================================


class PatientResponse(BaseModel):
    """Schema for patient API responses."""

    patient_id: str
    nombre: str
    apellido: str
    fecha_nacimiento: str
    genero: str | None
    curp: str | None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class CurpValidationResponse(BaseModel):
    """Schema for CURP validation response."""

    valid: bool = Field(..., description="Whether CURP format is valid")
    available: bool = Field(..., description="Whether CURP is available (not in use)")
    message: str | None = Field(None, description="Error or info message")


__all__ = [
    "GenderEnum",
    "PatientCreate",
    "PatientUpdate",
    "PatientResponse",
    "CurpValidationRequest",
    "CurpValidationResponse",
]
