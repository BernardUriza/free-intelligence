"""SOAP Notes Models - Request/Response schemas for SOAP workflow.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.domain.soap.models import SOAPNote


# ============================================================================
# Request Schemas
# ============================================================================


class SOAPUpdateRequest(BaseModel):
    """Request body for SOAP update."""

    soap: SOAPNote = Field(..., description="Complete validated SOAP data structure")

    @field_validator("soap", mode="before")
    @classmethod
    def validate_soap_structure(cls, v: Any) -> dict:
        """Validate SOAP structure before creating the model."""
        if isinstance(v, dict):
            # Check if required sections exist
            required_sections = ["subjective", "objective", "assessment", "plan"]
            for section in required_sections:
                if section not in v:
                    raise ValueError(f"Missing required section: {section}")

            # Create and validate the SOAPNote instance
            try:
                soap_note = SOAPNote.model_validate(v)
                validation_errors = soap_note.validate_completeness()
                if validation_errors:
                    raise ValueError(f"SOAP note validation failed: {'; '.join(validation_errors)}")
                return soap_note
            except Exception as e:
                raise ValueError(f"Invalid SOAP structure: {e!s}")
        return v


class AssistantRequest(BaseModel):
    """Request body for SOAP assistant natural language commands."""

    command: str = Field(
        ...,
        min_length=1,
        description="Natural language command to modify SOAP data",
        examples=["agrega que la paciente tiene diabetes", "nota: paciente vive con VIH"],
    )
    current_soap: dict[str, Any] = Field(
        ..., description="Current SOAP data structure to be modified"
    )


# ============================================================================
# Response Schemas
# ============================================================================


class AssistantResponse(BaseModel):
    """Response from SOAP assistant with structured updates."""

    updates: dict[str, str | dict] = Field(
        ...,
        description="Dictionary of SOAP field updates (field_name: operation:content or complex object)",
    )
    explanation: str = Field(..., description="Human-readable explanation of changes")
    success: bool = Field(default=True, description="Whether operation succeeded")
