"""SOAP Note mapper - DTO to Entity conversions.

Author: Claude Code
Created: 2026-01-28
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from backend.domain.soap.entity import SOAPNote, SOAPStatus


class SOAPMapper:
    """Maps between SOAP representations."""

    @staticmethod
    def from_hdf5(soap_id: str, metadata: Dict[str, Any], content: Dict[str, str]) -> SOAPNote:
        """Convert HDF5 data to domain entity."""
        return SOAPNote(
            soap_id=soap_id,
            session_id=metadata["session_id"],
            subjetivo=content.get("subjetivo", ""),
            objetivo=content.get("objetivo", ""),
            analisis=content.get("analisis", ""),
            plan=content.get("plan", ""),
            status=SOAPStatus(metadata.get("status", "draft")),
            created_at=datetime.fromisoformat(
                metadata.get("created_at", datetime.utcnow().isoformat())
            ),
            updated_at=datetime.fromisoformat(
                metadata.get("updated_at", datetime.utcnow().isoformat())
            ),
            reviewed_at=(
                datetime.fromisoformat(metadata["reviewed_at"])
                if metadata.get("reviewed_at")
                else None
            ),
            approved_at=(
                datetime.fromisoformat(metadata["approved_at"])
                if metadata.get("approved_at")
                else None
            ),
            quality_score=metadata.get("quality_score"),
            completeness=metadata.get("completeness"),
            nom_compliance=metadata.get("nom_compliance"),
            medico=metadata.get("medico"),
            especialidad=metadata.get("especialidad"),
        )

    @staticmethod
    def to_hdf5(entity: SOAPNote) -> tuple[Dict[str, Any], Dict[str, str]]:
        """Convert domain entity to HDF5 format.

        Returns:
            (metadata dict, content dict)
        """
        metadata = {
            "session_id": entity.session_id,
            "status": entity.status.value,
            "created_at": entity.created_at.isoformat(),
            "updated_at": entity.updated_at.isoformat(),
            "reviewed_at": entity.reviewed_at.isoformat() if entity.reviewed_at else None,
            "approved_at": entity.approved_at.isoformat() if entity.approved_at else None,
            "quality_score": entity.quality_score,
            "completeness": entity.completeness,
            "nom_compliance": entity.nom_compliance,
            "medico": entity.medico,
            "especialidad": entity.especialidad,
        }

        content = {
            "subjetivo": entity.subjetivo,
            "objetivo": entity.objetivo,
            "analisis": entity.analisis,
            "plan": entity.plan,
        }

        return metadata, content
