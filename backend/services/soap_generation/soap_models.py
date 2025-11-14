"""Pydantic models for SOAP (Subjective-Objective-Assessment-Plan) data structure.

Defines the expected schema for medical SOAP notes extracted from transcriptions.
All fields support multilingual content with English field names (medical standard).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from typing import List

__all__ = ["SubjetiveData", "ObjetivoData", "AnalisisData", "PlanData", "SOAPNote"]


class SubjetiveData(BaseModel):
    """Subjective (patient-reported) section of SOAP note.

    Contains patient's chief complaint, symptom history, and medical background
    in their original language without translation.
    """

    motivo_consulta: str = Field(
        ...,
        description="Chief complaint: main reason for consultation",
        min_length=1,
    )
    historia_actual: str = Field(
        ...,
        description="History of present illness: detailed symptom description",
        min_length=1,
    )
    antecedentes: str = Field(
        ...,
        description="Medical history: relevant past medical events",
        min_length=1,
    )

    model_config = ConfigDict(extra="allow")


class ObjetivoData(BaseModel):
    """Objective (clinician-observed) section of SOAP note.

    Contains vital signs, physical examination findings, and measurable data.
    """

    signos_vitales: str = Field(
        ...,
        description="Vital signs: BP, temperature, heart rate, respiration rate",
        min_length=1,
    )
    examen_fisico: str = Field(
        ...,
        description="Physical examination findings",
        min_length=1,
    )

    model_config = ConfigDict(extra="allow")


class AnalisisData(BaseModel):
    """Assessment (analysis and diagnosis) section of SOAP note.

    Contains differential diagnoses and primary diagnosis determination.
    """

    diagnosticos_diferenciales: List[str] = Field(
        default_factory=list,
        description="Differential diagnoses list",
    )
    diagnostico_principal: str = Field(
        ...,
        description="Primary diagnosis: most likely condition",
        min_length=1,
    )

    @field_validator("diagnosticos_diferenciales", mode="before")
    @classmethod
    def ensure_list(cls, v: List[str] | str) -> list[str]:
        """Ensure diagnosticos_diferenciales is always a list."""
        if isinstance(v, str):
            return [v]
        return v if v else []

    model_config = ConfigDict(extra="allow")


class PlanData(BaseModel):
    """Plan (treatment and follow-up) section of SOAP note.

    Contains medications, interventions, follow-up instructions, and studies.
    """

    tratamiento: str = Field(
        ...,
        description="Treatment plan: medications and interventions",
        min_length=1,
    )
    seguimiento: str = Field(
        ...,
        description="Follow-up instructions",
        min_length=1,
    )
    estudios: List[str] = Field(
        default_factory=list,
        description="Recommended studies or diagnostic tests",
    )

    @field_validator("estudios", mode="before")
    @classmethod
    def ensure_list(cls, v: List[str] | str) -> list[str]:
        """Ensure estudios is always a list."""
        if isinstance(v, str):
            return [v]
        return v if v else []

    model_config = ConfigDict(extra="allow")


class SOAPNote(BaseModel):
    """Complete SOAP (Subjective-Objective-Assessment-Plan) medical note.

    Represents a structured medical consultation note with four main sections.
    Validates that all required fields are present and properly structured.
    """

    subjetivo: SubjetiveData = Field(
        ...,
        description="Subjective section (patient-reported)",
    )
    objetivo: ObjetivoData = Field(
        ...,
        description="Objective section (clinician-observed)",
    )
    analisis: AnalisisData = Field(
        ...,
        description="Assessment section (diagnosis)",
    )
    plan: PlanData = Field(
        ...,
        description="Plan section (treatment and follow-up)",
    )

    model_config = ConfigDict(extra="allow")

    def to_dict(self) -> dict:
        """Convert SOAP note to dictionary with nested structure.

        Returns:
            Dictionary representation of the complete SOAP note.
        """
        return self.model_dump(mode="json")

    def validate_completeness(self) -> list[str]:
        """Validate that all required fields are present and non-empty.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: List[str] = []

        # Check subjective
        if not self.subjetivo.motivo_consulta.strip():
            errors.append("subjetivo.motivo_consulta is empty")
        if not self.subjetivo.historia_actual.strip():
            errors.append("subjetivo.historia_actual is empty")
        if not self.subjetivo.antecedentes.strip():
            errors.append("subjetivo.antecedentes is empty")

        # Check objetivo
        if not self.objetivo.signos_vitales.strip():
            errors.append("objetivo.signos_vitales is empty")
        if not self.objetivo.examen_fisico.strip():
            errors.append("objetivo.examen_fisico is empty")

        # Check analisis
        if not self.analisis.diagnostico_principal.strip():
            errors.append("analisis.diagnostico_principal is empty")

        # Check plan
        if not self.plan.tratamiento.strip():
            errors.append("plan.tratamiento is empty")
        if not self.plan.seguimiento.strip():
            errors.append("plan.seguimiento is empty")

        return errors
