"""SOAP Note mapper - DTO to Entity conversions.

Author: Claude Code
Created: 2026-01-28
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.domain.soap.entity import SOAPNote, SOAPStatus


@dataclass
class SOAPHDF5Metadata:
    """Typed HDF5 metadata for SOAP Note (Fix #3 - Type Safety).

    All fields REQUIRED (no .get() defaults).
    """

    session_id: str
    status: str  # SOAPStatus.value
    created_at: str  # ISO format
    updated_at: str  # ISO format
    reviewed_at: str | None
    approved_at: str | None
    quality_score: float | None
    completeness: float | None
    nom_compliance: float | None
    medico: str | None
    especialidad: str | None


@dataclass
class SOAPHDF5Content:
    """Typed HDF5 content for SOAP Note (Fix #3 - Type Safety).

    SOAP sections (Subjetivo, Objetivo, Analisis, Plan).
    """

    subjetivo: str
    objetivo: str
    analisis: str
    plan: str


class SOAPMapper:
    """Maps between SOAP representations."""

    @staticmethod
    def from_hdf5(soap_id: str, metadata: SOAPHDF5Metadata, content: SOAPHDF5Content) -> SOAPNote:
        """Convert HDF5 data to domain entity (Fix #3 - Type Safety).

        Args:
            soap_id: SOAP Note UUID
            metadata: TYPED HDF5 metadata
            content: TYPED HDF5 content (SOAP sections)

        Returns:
            SOAPNote domain entity

        Raises:
            AttributeError: If metadata/content missing required fields
            ValueError: If datetime strings invalid
        """
        return SOAPNote(
            soap_id=soap_id,
            session_id=metadata.session_id,
            subjetivo=content.subjetivo,
            objetivo=content.objetivo,
            analisis=content.analisis,
            plan=content.plan,
            status=SOAPStatus(metadata.status),
            created_at=datetime.fromisoformat(metadata.created_at),
            updated_at=datetime.fromisoformat(metadata.updated_at),
            reviewed_at=(
                datetime.fromisoformat(metadata.reviewed_at)
                if metadata.reviewed_at
                else None
            ),
            approved_at=(
                datetime.fromisoformat(metadata.approved_at)
                if metadata.approved_at
                else None
            ),
            quality_score=metadata.quality_score,
            completeness=metadata.completeness,
            nom_compliance=metadata.nom_compliance,
            medico=metadata.medico,
            especialidad=metadata.especialidad,
        )

    @staticmethod
    def to_hdf5(entity: SOAPNote) -> tuple[SOAPHDF5Metadata, SOAPHDF5Content]:
        """Convert domain entity to HDF5 format (Fix #3 - Type Safety).

        Returns:
            (TYPED metadata, TYPED content) - use dataclasses.asdict() in repository
        """
        metadata = SOAPHDF5Metadata(
            session_id=entity.session_id,
            status=entity.status.value,
            created_at=entity.created_at.isoformat(),
            updated_at=entity.updated_at.isoformat(),
            reviewed_at=entity.reviewed_at.isoformat() if entity.reviewed_at else None,
            approved_at=entity.approved_at.isoformat() if entity.approved_at else None,
            quality_score=entity.quality_score,
            completeness=entity.completeness,
            nom_compliance=entity.nom_compliance,
            medico=entity.medico,
            especialidad=entity.especialidad,
        )

        content = SOAPHDF5Content(
            subjetivo=entity.subjetivo,
            objetivo=entity.objetivo,
            analisis=entity.analisis,
            plan=entity.plan,
        )

        return metadata, content
