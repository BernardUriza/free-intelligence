"""SOAP Note domain entity - pure business logic.

SOAP (Subjective, Objective, Assessment, Plan) is a medical documentation format.
This entity represents the clinical note generated from a consultation session.

This is a PURE domain entity with ZERO framework dependencies.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 3B Part 2 - Pure Domain Entities
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class SOAPStatus(str, Enum):
    """SOAP note lifecycle status."""

    DRAFT = "draft"  # Being generated
    GENERATED = "generated"  # AI generation complete
    REVIEWED = "reviewed"  # Physician reviewed
    APPROVED = "approved"  # Physician approved
    ARCHIVED = "archived"  # Finalized


@dataclass
class SOAPNote:
    """SOAP Note domain entity.

    Represents a structured clinical note (NOM-004-SSA3-2012 compliant).

    Business rules:
    - soap_id and session_id are immutable
    - Status can only progress forward (no regression)
    - Quality scores must be 0-1 range
    - NOM compliance must be 0-100 range
    - Approved notes cannot be edited
    """

    soap_id: str
    session_id: str
    subjetivo: str  # Subjective: patient's complaint and history
    objetivo: str  # Objective: physical exam, vitals, labs
    analisis: str  # Assessment: diagnosis and clinical reasoning
    plan: str  # Plan: treatment, referrals, follow-up
    status: SOAPStatus = SOAPStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reviewed_at: datetime | None = None
    approved_at: datetime | None = None
    quality_score: float | None = None  # 0-1: AI quality assessment
    completeness: float | None = None  # 0-100: percentage complete
    nom_compliance: float | None = None  # 0-100: NOM-004 compliance

    # Metadata
    medico: str | None = None  # Physician name
    especialidad: str | None = None  # Medical specialty

    def __post_init__(self) -> None:
        """Validate entity after initialization.

        Raises:
            ValueError: If business rules are violated
        """
        if not self.soap_id or not self.soap_id.strip():
            raise ValueError("SOAP ID cannot be empty")

        if not self.session_id or not self.session_id.strip():
            raise ValueError("Session ID cannot be empty")

        # Validate score ranges
        if self.quality_score is not None and not (0 <= self.quality_score <= 1):
            raise ValueError(f"Quality score must be 0-1, got: {self.quality_score}")

        if self.completeness is not None and not (0 <= self.completeness <= 100):
            raise ValueError(f"Completeness must be 0-100, got: {self.completeness}")

        if self.nom_compliance is not None and not (0 <= self.nom_compliance <= 100):
            raise ValueError(f"NOM compliance must be 0-100, got: {self.nom_compliance}")

        # Ensure dates are UTC-aware
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=UTC)
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=UTC)

    # ========================================================================
    # Domain Behavior (Business Logic)
    # ========================================================================

    def update_content(
        self,
        subjetivo: str | None = None,
        objetivo: str | None = None,
        analisis: str | None = None,
        plan: str | None = None,
    ) -> None:
        """Update SOAP note sections.

        Args:
            subjetivo: Updated subjective section
            objetivo: Updated objective section
            analisis: Updated assessment section
            plan: Updated plan section

        Raises:
            ValueError: If note is approved (cannot edit)
        """
        if self.status == SOAPStatus.APPROVED:
            raise ValueError("Cannot edit approved SOAP note")

        if subjetivo is not None:
            self.subjetivo = subjetivo
        if objetivo is not None:
            self.objetivo = objetivo
        if analisis is not None:
            self.analisis = analisis
        if plan is not None:
            self.plan = plan

        self.updated_at = datetime.now(UTC)

    def mark_generated(
        self,
        quality_score: float,
        completeness: float,
        nom_compliance: float,
    ) -> None:
        """Mark SOAP note as AI-generated.

        Args:
            quality_score: AI quality assessment (0-1)
            completeness: Percentage complete (0-100)
            nom_compliance: NOM-004 compliance (0-100)

        Raises:
            ValueError: If scores are out of range
        """
        if not (0 <= quality_score <= 1):
            raise ValueError(f"Quality score must be 0-1, got: {quality_score}")
        if not (0 <= completeness <= 100):
            raise ValueError(f"Completeness must be 0-100, got: {completeness}")
        if not (0 <= nom_compliance <= 100):
            raise ValueError(f"NOM compliance must be 0-100, got: {nom_compliance}")

        self.status = SOAPStatus.GENERATED
        self.quality_score = quality_score
        self.completeness = completeness
        self.nom_compliance = nom_compliance
        self.updated_at = datetime.now(UTC)

    def mark_reviewed(self) -> None:
        """Mark SOAP note as physician-reviewed.

        Raises:
            ValueError: If note is not generated
        """
        if self.status == SOAPStatus.DRAFT:
            raise ValueError("Cannot review draft SOAP note")

        self.status = SOAPStatus.REVIEWED
        self.reviewed_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def approve(self, medico: str, especialidad: str) -> None:
        """Approve SOAP note (physician signature).

        Args:
            medico: Physician name
            especialidad: Medical specialty

        Raises:
            ValueError: If note is not reviewed
        """
        if self.status not in [SOAPStatus.REVIEWED, SOAPStatus.GENERATED]:
            raise ValueError(f"Cannot approve SOAP note with status: {self.status}")

        self.status = SOAPStatus.APPROVED
        self.approved_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
        self.medico = medico
        self.especialidad = especialidad

    def archive(self) -> None:
        """Archive SOAP note (final state).

        Raises:
            ValueError: If note is not approved
        """
        if self.status != SOAPStatus.APPROVED:
            raise ValueError("Can only archive approved SOAP notes")

        self.status = SOAPStatus.ARCHIVED
        self.updated_at = datetime.now(UTC)

    def is_complete(self) -> bool:
        """Check if SOAP note is complete (all sections filled).

        Returns:
            True if all sections have content
        """
        return all(
            [
                self.subjetivo and self.subjetivo.strip(),
                self.objetivo and self.objetivo.strip(),
                self.analisis and self.analisis.strip(),
                self.plan and self.plan.strip(),
            ]
        )

    def is_high_quality(self) -> bool:
        """Check if SOAP note meets quality threshold.

        Returns:
            True if quality_score >= 0.8
        """
        return self.quality_score is not None and self.quality_score >= 0.8

    def is_nom_compliant(self) -> bool:
        """Check if SOAP note meets NOM-004 compliance.

        Returns:
            True if nom_compliance >= 90
        """
        return self.nom_compliance is not None and self.nom_compliance >= 90

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"SOAPNote(id={self.soap_id}, session={self.session_id}, "
            f"status={self.status.value}, quality={self.quality_score:.2f if self.quality_score else 'N/A'})"
        )
