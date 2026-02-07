"""SOAP Mapper - DB ↔ Domain mapping for SOAP notes.

Separates persistence structure (HDF5) from domain model (SOAPNote).

Pattern:
    Repository calls: SOAPMapper.to_hdf5(soap) → tuple[SOAPHDF5Metadata, SOAPHDF5Content]
    Repository calls: SOAPMapper.from_hdf5(soap_id, metadata, content) → SOAPNote

Author: Claude Code (P1-5 Repository Mappers)
Created: 2026-02-02
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from backend.domain.soap.models import (
    AssessmentData,
    ObjectiveData,
    PlanData,
    SOAPNote,
    SubjectiveData,
)


# ============================================================================
# HDF5 Persistence Structures
# ============================================================================


@dataclass
class SOAPHDF5Metadata:
    """Metadata for SOAP note persistence in HDF5.

    Includes identifiers, timestamps, and status tracking.
    Stored as JSON in HDF5 group attributes.
    """

    soap_id: str
    session_id: str
    created_at: str  # ISO 8601 format
    updated_at: str | None = None
    status: str = "draft"  # draft | final
    doctor_id: str | None = None
    version: int = 1


@dataclass
class SOAPHDF5Content:
    """Content sections for SOAP note persistence in HDF5.

    Contains the 4 SOAP sections as nested dictionaries.
    Stored as JSON in HDF5 group attributes.
    """

    subjective: dict[str, Any]  # SubjectiveData serialized
    objective: dict[str, Any]  # ObjectiveData serialized
    assessment: dict[str, Any]  # AssessmentData serialized
    plan: dict[str, Any]  # PlanData serialized


# ============================================================================
# SOAPMapper - Bidirectional Mapping
# ============================================================================


class SOAPMapper:
    """Maps SOAPNote domain entity ↔ HDF5 persistence structures.

    Responsibilities:
    - Convert SOAPNote → (SOAPHDF5Metadata, SOAPHDF5Content) for persistence
    - Convert (SOAPHDF5Metadata, SOAPHDF5Content) → SOAPNote for domain use
    - Handle field transformations (datetime serialization, nested objects)
    """

    @staticmethod
    def to_hdf5(soap: SOAPNote) -> tuple[SOAPHDF5Metadata, SOAPHDF5Content]:
        """Convert SOAPNote domain entity to HDF5 persistence structures.

        Args:
            soap: SOAPNote entity from domain layer

        Returns:
            Tuple of (metadata, content) for HDF5 storage

        Example:
            >>> soap = SOAPNote(soap_id="123", session_id="456", ...)
            >>> metadata, content = SOAPMapper.to_hdf5(soap)
            >>> # Store in HDF5: group.attrs["metadata"] = json.dumps(asdict(metadata))
        """
        # Extract metadata fields (use getattr with defaults for dynamic fields)
        soap_id = getattr(soap, "soap_id", None)
        session_id = getattr(soap, "session_id", None)
        created_at = getattr(soap, "created_at", None)
        updated_at = getattr(soap, "updated_at", None)
        status = getattr(soap, "status", "draft")
        doctor_id = getattr(soap, "doctor_id", None)
        version = getattr(soap, "version", 1)

        # Validate required fields
        if not soap_id:
            raise ValueError("SOAPNote.soap_id is required for persistence")
        if not session_id:
            raise ValueError("SOAPNote.session_id is required for persistence")

        # Serialize datetime if needed
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        elif created_at is None:
            created_at = datetime.now().isoformat()

        if isinstance(updated_at, datetime):
            updated_at = updated_at.isoformat()

        metadata = SOAPHDF5Metadata(
            soap_id=soap_id,
            session_id=session_id,
            created_at=created_at,
            updated_at=updated_at,
            status=status,
            doctor_id=doctor_id,
            version=version,
        )

        # Serialize content sections using Pydantic's model_dump
        content = SOAPHDF5Content(
            subjective=soap.subjective.model_dump(),
            objective=soap.objective.model_dump(),
            assessment=soap.assessment.model_dump(),
            plan=soap.plan.model_dump(),
        )

        return metadata, content

    @staticmethod
    def from_hdf5(
        soap_id: str, metadata: SOAPHDF5Metadata, content: SOAPHDF5Content
    ) -> SOAPNote:
        """Convert HDF5 persistence structures to SOAPNote domain entity.

        Args:
            soap_id: SOAP note identifier (for validation)
            metadata: SOAPHDF5Metadata from HDF5 attributes
            content: SOAPHDF5Content from HDF5 attributes

        Returns:
            SOAPNote domain entity with all fields populated

        Example:
            >>> metadata = SOAPHDF5Metadata(**json.loads(group.attrs["metadata"]))
            >>> content = SOAPHDF5Content(**json.loads(group.attrs["content"]))
            >>> soap = SOAPMapper.from_hdf5("123", metadata, content)
        """
        # Validate soap_id consistency
        if soap_id != metadata.soap_id:
            raise ValueError(
                f"soap_id mismatch: path={soap_id}, metadata={metadata.soap_id}"
            )

        # Reconstruct domain models from dictionaries
        subjective = SubjectiveData(**content.subjective)
        objective = ObjectiveData(**content.objective)
        assessment = AssessmentData(**content.assessment)
        plan = PlanData(**content.plan)

        # Create SOAPNote with Pydantic's extra="allow" for dynamic fields
        soap_dict = {
            "subjective": subjective,
            "objective": objective,
            "assessment": assessment,
            "plan": plan,
            # Add dynamic metadata fields
            "soap_id": metadata.soap_id,
            "session_id": metadata.session_id,
            "created_at": metadata.created_at,
            "updated_at": metadata.updated_at,
            "status": metadata.status,
            "doctor_id": metadata.doctor_id,
            "version": metadata.version,
        }

        return SOAPNote(**soap_dict)
