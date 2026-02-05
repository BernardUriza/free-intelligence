"""Allergy Models for Prescription Safety.

Defines structures for patient allergies, allergen-medication
cross-references, and allergy alerts.

Author: Bernard Uriza Orozco
Created: 2025-12-28
Card: FI-RX-009
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AllergySeverity(str, Enum):
    """Severity level of allergy reaction.

    Based on clinical classification:
    - MILD: Rash, itching, localized reactions
    - MODERATE: Systemic urticaria, angioedema
    - SEVERE: Anaphylaxis risk, contraindicated
    """

    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class AllergenType(str, Enum):
    """Type of allergen."""

    DRUG_CLASS = "drug_class"  # Penicillins, Sulfonamides, NSAIDs
    SPECIFIC_DRUG = "specific_drug"  # Specific medication
    EXCIPIENT = "excipient"  # Inactive ingredients (lactose, gluten)
    FOOD = "food"  # Food allergies affecting medication choice
    OTHER = "other"


class AllergenEntry(BaseModel):
    """An allergen with its related medications.

    Maps an allergen (e.g., "Penicilina") to all medications
    that should be avoided or used with caution.

    Attributes:
        id: Unique allergen identifier
        name: Allergen name (generic term)
        name_es: Allergen name in Spanish
        allergen_type: Type of allergen
        related_medications: Medications to avoid
        cross_reactive: Cross-reactive allergens
        severity: Default reaction severity
        notes: Clinical notes
    """

    id: str = Field(..., description="Unique allergen ID")

    name: str = Field(
        ...,
        description="Allergen name (English)",
    )

    name_es: str = Field(
        ...,
        description="Allergen name in Spanish",
    )

    allergen_type: AllergenType = Field(
        default=AllergenType.DRUG_CLASS,
        description="Type of allergen",
    )

    related_medications: list[str] = Field(
        default_factory=list,
        description="Medications that contain or are related to this allergen",
    )

    cross_reactive: list[str] = Field(
        default_factory=list,
        description="Other allergens that may cause cross-reaction",
    )

    severity: AllergySeverity = Field(
        default=AllergySeverity.SEVERE,
        description="Default severity of reactions",
    )

    notes: str | None = Field(
        default=None,
        description="Clinical notes about this allergen",
    )

    notes_es: str | None = Field(
        default=None,
        description="Clinical notes in Spanish",
    )

    is_active: bool = Field(
        default=True,
        description="Whether this allergen is active in the database",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "penicillin",
                "name": "Penicillin",
                "name_es": "Penicilina",
                "allergen_type": "drug_class",
                "related_medications": [
                    "Amoxicilina",
                    "Ampicilina",
                    "Penicilina V",
                    "Penicilina G",
                    "Dicloxacilina",
                ],
                "cross_reactive": ["cefalosporinas"],
                "severity": "severe",
                "notes_es": "Riesgo de anafilaxia. 10% reacción cruzada con cefalosporinas.",
            }
        },
    )

    def matches_medication(self, medication_name: str) -> bool:
        """Check if a medication matches this allergen.

        Args:
            medication_name: Medication name to check

        Returns:
            True if medication is related to this allergen
        """
        med_lower = medication_name.lower()

        # Check direct match in related medications
        for related in self.related_medications:
            if related.lower() in med_lower or med_lower in related.lower():
                return True

        # Check if allergen name is contained in medication name
        if self.name.lower() in med_lower or self.name_es.lower() in med_lower:
            return True

        return False


class AllergyAlert(BaseModel):
    """Alert generated when medication matches patient allergy.

    Attributes:
        allergen: The matched allergen
        medication_name: Name of medication that triggered alert
        patient_allergy: Original allergy from patient record
        severity: Severity of potential reaction
        alert_message: User-friendly alert message
        can_override: Whether physician can override
    """

    allergen: AllergenEntry = Field(
        ...,
        description="The allergen that was matched",
    )

    medication_name: str = Field(
        ...,
        description="Medication that triggered the alert",
    )

    patient_allergy: str = Field(
        ...,
        description="Original allergy from patient record",
    )

    severity: AllergySeverity = Field(
        ...,
        description="Severity of potential reaction",
    )

    alert_message: str = Field(
        ...,
        description="User-friendly alert message in Spanish",
    )

    can_override: bool = Field(
        default=False,
        description="Whether this alert can be overridden",
    )

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_allergen(
        cls,
        allergen: AllergenEntry,
        medication_name: str,
        patient_allergy: str,
    ) -> "AllergyAlert":
        """Create an alert from an allergen match.

        Args:
            allergen: The matched allergen
            medication_name: Medication that matched
            patient_allergy: Patient's recorded allergy

        Returns:
            AllergyAlert instance
        """
        severity_labels = {
            AllergySeverity.MILD: "LEVE",
            AllergySeverity.MODERATE: "MODERADA",
            AllergySeverity.SEVERE: "GRAVE",
        }

        severity_label = severity_labels[allergen.severity]

        message = (
            f"⚠️ ALERGIA {severity_label}: {medication_name}\n"
            f"Paciente alérgico a: {patient_allergy}\n"
        )

        if allergen.notes_es:
            message += f"Nota: {allergen.notes_es}"

        # Severe allergies cannot be overridden
        can_override = allergen.severity != AllergySeverity.SEVERE

        return cls(
            allergen=allergen,
            medication_name=medication_name,
            patient_allergy=patient_allergy,
            severity=allergen.severity,
            alert_message=message,
            can_override=can_override,
        )


class AllergyCheckResult(BaseModel):
    """Result of checking medications against patient allergies.

    Attributes:
        medications_checked: List of medications checked
        patient_allergies: Patient's recorded allergies
        alerts: List of allergy alerts
        has_severe_allergies: Whether severe allergy matches found
        can_proceed: Whether prescription can proceed
        summary: Summary message
    """

    medications_checked: list[str] = Field(
        ...,
        description="Medications that were checked",
    )

    patient_allergies: list[str] = Field(
        ...,
        description="Patient's recorded allergies",
    )

    alerts: list[AllergyAlert] = Field(
        default_factory=list,
        description="Allergy alerts generated",
    )

    has_severe_allergies: bool = Field(
        default=False,
        description="Whether severe allergy matches were found",
    )

    can_proceed: bool = Field(
        default=True,
        description="Whether prescription can proceed (no severe allergies)",
    )

    summary: str = Field(
        default="",
        description="Summary message in Spanish",
    )

    model_config = ConfigDict(extra="forbid")

    @property
    def alert_count(self) -> int:
        """Total number of alerts."""
        return len(self.alerts)

    @property
    def severe_count(self) -> int:
        """Number of severe allergy alerts."""
        return sum(1 for a in self.alerts if a.severity == AllergySeverity.SEVERE)

    @property
    def moderate_count(self) -> int:
        """Number of moderate allergy alerts."""
        return sum(1 for a in self.alerts if a.severity == AllergySeverity.MODERATE)

    @property
    def mild_count(self) -> int:
        """Number of mild allergy alerts."""
        return sum(1 for a in self.alerts if a.severity == AllergySeverity.MILD)
