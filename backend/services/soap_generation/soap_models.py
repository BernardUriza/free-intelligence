"""Pydantic models for SOAP (Subjective-Objective-Assessment-Plan) data structure.

Defines the expected schema for medical SOAP notes extracted from transcriptions.
All fields support multilingual content with English field names (medical standard).
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["AssessmentData", "ObjectiveData", "PlanData", "SOAPNote", "SubjectiveData"]


class SubjectiveData(BaseModel):
    """Subjective (patient-reported) section of SOAP note.

    Contains patient's chief complaint, symptom history, and medical background
    in their original language without translation.
    """

    chief_complaint: str = Field(
        ...,
        description="Chief complaint: main reason for consultation",
        min_length=1,
    )
    history_present_illness: str = Field(
        ...,
        description="History of present illness: detailed symptom description",
        min_length=1,
    )
    past_medical_history: str = Field(
        ...,
        description="Medical history: relevant past medical events",
        min_length=1,
    )

    model_config = ConfigDict(extra="allow")


class ObjectiveData(BaseModel):
    """Objective (clinician-observed) section of SOAP note.

    Contains vital signs, physical examination findings, and measurable data.
    """

    vital_signs: str = Field(
        ...,
        description="Vital signs: BP, temperature, heart rate, respiration rate",
        min_length=1,
    )
    physical_exam: str = Field(
        ...,
        description="Physical examination findings",
        min_length=1,
    )

    model_config = ConfigDict(extra="allow")


class AssessmentData(BaseModel):
    """Assessment (analysis and diagnosis) section of SOAP note.

    Contains differential diagnoses and primary diagnosis determination.
    """

    differential_diagnoses: List[str] = Field(
        default_factory=list,
        description="Differential diagnoses list",
    )
    primary_diagnosis: str = Field(
        ...,
        description="Primary diagnosis: most likely condition",
        min_length=1,
    )

    @field_validator("differential_diagnoses", mode="before")
    @classmethod
    def ensure_list(cls, v: List[str] | str) -> list[str]:
        """Ensure differential_diagnoses is always a list."""
        if isinstance(v, str):
            return [v]
        return v if v else []

    model_config = ConfigDict(extra="allow")


class PlanData(BaseModel):
    """Plan (treatment and follow-up) section of SOAP note.

    Contains medications, interventions, follow-up instructions, and studies.
    """

    treatment: str = Field(
        ...,
        description="Treatment plan: medications and interventions",
        min_length=1,
    )
    follow_up: str = Field(
        ...,
        description="Follow-up instructions",
        min_length=1,
    )
    studies: List[str] = Field(
        default_factory=list,
        description="Recommended studies or diagnostic tests",
    )

    @field_validator("studies", mode="before")
    @classmethod
    def ensure_list(cls, v: List[str] | str) -> list[str]:
        """Ensure studies is always a list."""
        if isinstance(v, str):
            return [v]
        return v if v else []

    model_config = ConfigDict(extra="allow")


class SOAPNote(BaseModel):
    """Complete SOAP (Subjective-Objective-Assessment-Plan) medical note.

    Represents a structured medical consultation note with four main sections.
    Validates that all required fields are present and properly structured.
    """

    subjective: SubjectiveData = Field(
        ...,
        description="Subjective section (patient-reported)",
    )
    objective: ObjectiveData = Field(
        ...,
        description="Objective section (clinician-observed)",
    )
    assessment: AssessmentData = Field(
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
        if not self.subjective.chief_complaint.strip():
            errors.append("subjective.chief_complaint is empty")
        if not self.subjective.history_present_illness.strip():
            errors.append("subjective.history_present_illness is empty")
        if not self.subjective.past_medical_history.strip():
            errors.append("subjective.past_medical_history is empty")

        # Check objective
        if not self.objective.vital_signs.strip():
            errors.append("objective.vital_signs is empty")
        if not self.objective.physical_exam.strip():
            errors.append("objective.physical_exam is empty")

        # Check assessment
        if not self.assessment.primary_diagnosis.strip():
            errors.append("assessment.primary_diagnosis is empty")

        # Check plan
        if not self.plan.treatment.strip():
            errors.append("plan.treatment is empty")
        if not self.plan.follow_up.strip():
            errors.append("plan.follow_up is empty")

        return errors
