"""Prescription API Request/Response Models.

Pydantic models for prescription endpoints.
Extracted from monolithic prescriptions.py for modularity.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.domain.prescription.models.medication import Medication
from backend.domain.prescription.models.prescription import (
    PatientInfo,
    PhysicianInfo,
    Prescription,
)
from backend.domain.prescription.models.template import PrescriptionTemplate


# ============================================================================
# Prescription Request Models
# ============================================================================


class CreatePrescriptionRequest(BaseModel):
    """Request body for creating a prescription."""

    template_id: str = Field(
        default="default",
        description="Template ID to use",
    )
    session_id: str | None = Field(
        default=None,
        description="Session ID to link prescription",
    )
    patient: PatientInfo = Field(
        ...,
        description="Patient information",
    )
    physician: PhysicianInfo = Field(
        ...,
        description="Physician information",
    )
    diagnosis: str = Field(
        ...,
        min_length=1,
        description="Primary diagnosis",
    )
    diagnosis_code: str | None = Field(
        default=None,
        description="ICD-10 code",
    )
    medications: list[Medication] = Field(
        ...,
        min_length=1,
        description="List of medications",
    )
    general_instructions: str | None = Field(
        default=None,
        description="General instructions for patient",
    )
    next_appointment: str | None = Field(
        default=None,
        description="Next appointment info",
    )


class UpdatePrescriptionRequest(BaseModel):
    """Request body for updating a prescription."""

    diagnosis: str | None = Field(default=None)
    diagnosis_code: str | None = Field(default=None)
    medications: list[Medication] | None = Field(default=None)
    general_instructions: str | None = Field(default=None)
    next_appointment: str | None = Field(default=None)
    patient: PatientInfo | None = Field(default=None)


class CreateFromSOAPRequest(BaseModel):
    """Request body for creating prescription from SOAP data."""

    session_id: str = Field(
        ...,
        description="Session ID containing SOAP data",
    )
    template_id: str = Field(
        default="default",
        description="Template ID to use",
    )
    patient: PatientInfo = Field(
        ...,
        description="Patient information",
    )
    physician: PhysicianInfo = Field(
        ...,
        description="Physician information",
    )


class CancelPrescriptionRequest(BaseModel):
    """Request body for cancelling a prescription."""

    reason: str | None = Field(
        default=None,
        max_length=500,
        description="Cancellation reason",
    )


# ============================================================================
# Prescription Response Models
# ============================================================================


class PrescriptionResponse(BaseModel):
    """Standard response for prescription operations."""

    success: bool = Field(default=True)
    prescription: Prescription | None = Field(default=None)
    message: str | None = Field(default=None)


class TemplateListResponse(BaseModel):
    """Response for template list."""

    templates: list[PrescriptionTemplate]
    count: int


class PrescriptionListResponse(BaseModel):
    """Response for prescription list."""

    prescriptions: list[Prescription]
    count: int


# ============================================================================
# Interaction Request Models
# ============================================================================


class CheckInteractionsRequest(BaseModel):
    """Request body for checking drug interactions."""

    medications: list[str] = Field(
        ...,
        min_length=2,
        description="List of medication names to check",
    )


class CheckPrescriptionInteractionsRequest(BaseModel):
    """Request body for checking interactions with Medication objects."""

    medications: list[Medication] = Field(
        ...,
        min_length=2,
        description="List of Medication objects to check",
    )


# ============================================================================
# Allergy Request Models
# ============================================================================


class CheckAllergiesRequest(BaseModel):
    """Request body for checking allergies."""

    medications: list[str] = Field(
        ...,
        min_length=1,
        description="List of medication names to check",
    )
    patient_allergies: list[str] = Field(
        ...,
        min_length=1,
        description="Patient's recorded allergies",
    )


class CheckAllergiesMedicationRequest(BaseModel):
    """Request body for checking allergies with Medication objects."""

    medications: list[Medication] = Field(
        ...,
        min_length=1,
        description="List of Medication objects to check",
    )
    patient_allergies: list[str] = Field(
        ...,
        min_length=1,
        description="Patient's recorded allergies",
    )


# ============================================================================
# Safety Request Models
# ============================================================================


class FullSafetyCheckRequest(BaseModel):
    """Request body for full safety check."""

    medications: list[Medication] = Field(
        ...,
        min_length=1,
        description="List of Medication objects to check",
    )
    patient_allergies: list[str] = Field(
        default_factory=list,
        description="Patient's recorded allergies (optional)",
    )
