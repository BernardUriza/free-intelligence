"""Drug Interaction Models.

Defines the structure for drug-drug interactions,
severity levels, and clinical recommendations.

Based on Mexican pharmaceutical guidelines and
international drug interaction databases.

Author: Bernard Uriza Orozco
Created: 2025-12-28
Card: FI-RX-008
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class InteractionSeverity(str, Enum):
    """Severity levels for drug interactions.

    Based on standard clinical classification:
    - MINOR: Usually no intervention needed
    - MODERATE: May require dose adjustment or monitoring
    - MAJOR: Avoid combination if possible
    - CONTRAINDICATED: Never use together
    """

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CONTRAINDICATED = "contraindicated"


class InteractionMechanism(str, Enum):
    """Mechanism of drug interaction."""

    PHARMACOKINETIC = "pharmacokinetic"  # Affects absorption, distribution, metabolism, excretion
    PHARMACODYNAMIC = "pharmacodynamic"  # Affects drug action at receptor level
    ADDITIVE = "additive"  # Combined effect equals sum of individual effects
    SYNERGISTIC = "synergistic"  # Combined effect greater than sum
    ANTAGONISTIC = "antagonistic"  # One drug reduces effect of another
    UNKNOWN = "unknown"


class DrugInteraction(BaseModel):
    """A drug-drug interaction entry.

    Represents an interaction between two medications,
    including severity, clinical effects, and recommendations.

    Attributes:
        id: Unique identifier
        drug_a: First drug (generic name or ID)
        drug_b: Second drug (generic name or ID)
        severity: Interaction severity level
        mechanism: How the interaction occurs
        effect: Clinical effect of the interaction
        recommendation: Clinical recommendation
        monitoring: Required monitoring if used together
        evidence_level: Quality of evidence (high, moderate, low)
        references: Literature references
    """

    id: str = Field(..., description="Unique interaction ID")

    drug_a: str = Field(
        ...,
        description="First drug (generic name)",
    )

    drug_b: str = Field(
        ...,
        description="Second drug (generic name)",
    )

    severity: InteractionSeverity = Field(
        ...,
        description="Severity level of interaction",
    )

    mechanism: InteractionMechanism = Field(
        default=InteractionMechanism.UNKNOWN,
        description="Mechanism of interaction",
    )

    effect: str = Field(
        ...,
        description="Clinical effect of the interaction",
    )

    effect_es: str = Field(
        ...,
        description="Clinical effect in Spanish",
    )

    recommendation: str = Field(
        ...,
        description="Clinical recommendation",
    )

    recommendation_es: str = Field(
        ...,
        description="Clinical recommendation in Spanish",
    )

    monitoring: str | None = Field(
        default=None,
        description="Required monitoring if used together",
    )

    onset: str | None = Field(
        default=None,
        description="Onset of interaction (immediate, delayed, variable)",
    )

    evidence_level: str = Field(
        default="moderate",
        description="Quality of evidence (high, moderate, low)",
    )

    references: list[str] = Field(
        default_factory=list,
        description="Literature references",
    )

    is_active: bool = Field(
        default=True,
        description="Whether this interaction is active in the database",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "warfarin_aspirin",
                "drug_a": "Warfarina",
                "drug_b": "Aspirina",
                "severity": "major",
                "mechanism": "pharmacodynamic",
                "effect": "Increased risk of bleeding",
                "effect_es": "Riesgo aumentado de sangrado",
                "recommendation": "Avoid combination or monitor closely",
                "recommendation_es": "Evitar combinación o monitorear de cerca",
                "monitoring": "INR, signs of bleeding",
                "evidence_level": "high",
            }
        },
    )

    def involves_drug(self, drug_name: str) -> bool:
        """Check if this interaction involves a specific drug.

        Args:
            drug_name: Drug name to check (case-insensitive)

        Returns:
            True if drug is involved in this interaction
        """
        drug_lower = drug_name.lower()
        return (
            drug_lower in self.drug_a.lower()
            or drug_lower in self.drug_b.lower()
            or self.drug_a.lower() in drug_lower
            or self.drug_b.lower() in drug_lower
        )

    def get_other_drug(self, drug_name: str) -> str | None:
        """Get the other drug in the interaction.

        Args:
            drug_name: Known drug name

        Returns:
            The other drug name, or None if drug not in interaction
        """
        drug_lower = drug_name.lower()
        if drug_lower in self.drug_a.lower() or self.drug_a.lower() in drug_lower:
            return self.drug_b
        if drug_lower in self.drug_b.lower() or self.drug_b.lower() in drug_lower:
            return self.drug_a
        return None


class InteractionAlert(BaseModel):
    """Alert generated when drug interactions are detected.

    Attributes:
        interaction: The detected interaction
        drug_1_name: Name of first drug as prescribed
        drug_2_name: Name of second drug as prescribed
        alert_message: User-friendly alert message
        can_override: Whether physician can override this alert
    """

    interaction: DrugInteraction = Field(
        ...,
        description="The detected interaction",
    )

    drug_1_name: str = Field(
        ...,
        description="First drug as prescribed",
    )

    drug_2_name: str = Field(
        ...,
        description="Second drug as prescribed",
    )

    alert_message: str = Field(
        ...,
        description="User-friendly alert message in Spanish",
    )

    can_override: bool = Field(
        default=True,
        description="Whether this alert can be overridden",
    )

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_interaction(
        cls,
        interaction: DrugInteraction,
        drug_1_name: str,
        drug_2_name: str,
    ) -> "InteractionAlert":
        """Create an alert from an interaction.

        Args:
            interaction: The detected interaction
            drug_1_name: First drug as prescribed
            drug_2_name: Second drug as prescribed

        Returns:
            InteractionAlert instance
        """
        severity_labels = {
            InteractionSeverity.MINOR: "MENOR",
            InteractionSeverity.MODERATE: "MODERADA",
            InteractionSeverity.MAJOR: "MAYOR",
            InteractionSeverity.CONTRAINDICATED: "CONTRAINDICADA",
        }

        severity_label = severity_labels[interaction.severity]

        message = (
            f"⚠️ INTERACCIÓN {severity_label}: {drug_1_name} + {drug_2_name}\n"
            f"Efecto: {interaction.effect_es}\n"
            f"Recomendación: {interaction.recommendation_es}"
        )

        # Contraindicated interactions cannot be overridden
        can_override = interaction.severity != InteractionSeverity.CONTRAINDICATED

        return cls(
            interaction=interaction,
            drug_1_name=drug_1_name,
            drug_2_name=drug_2_name,
            alert_message=message,
            can_override=can_override,
        )


class InteractionCheckResult(BaseModel):
    """Result of checking medications for interactions.

    Attributes:
        medications_checked: List of medication names checked
        alerts: List of interaction alerts found
        has_major_interactions: Whether any major/contraindicated found
        can_proceed: Whether prescription can proceed
        summary: Summary message
    """

    medications_checked: list[str] = Field(
        ...,
        description="List of medications that were checked",
    )

    alerts: list[InteractionAlert] = Field(
        default_factory=list,
        description="List of interaction alerts",
    )

    has_major_interactions: bool = Field(
        default=False,
        description="Whether major or contraindicated interactions were found",
    )

    can_proceed: bool = Field(
        default=True,
        description="Whether prescription can proceed (no contraindications)",
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
    def contraindicated_count(self) -> int:
        """Number of contraindicated interactions."""
        return sum(
            1 for a in self.alerts if a.interaction.severity == InteractionSeverity.CONTRAINDICATED
        )

    @property
    def major_count(self) -> int:
        """Number of major interactions."""
        return sum(1 for a in self.alerts if a.interaction.severity == InteractionSeverity.MAJOR)
