#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Evidence API

FastAPI router for evidence packs.

Updated to use clean code architecture with EvidenceService.

File: backend/api/evidence.py
Card: FI-DATA-RES-021
Created: 2025-10-30
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.container import get_container

logger = logging.getLogger(__name__)


class ClinicalSourceRequest(BaseModel):
    """Clinical source request"""

    source_id: str
    tipo_doc: str
    fecha: str
    paciente_id: str
    hallazgo: Optional[str] = None
    severidad: Optional[str] = None
    raw_text: Optional[str] = None


class CreateEvidencePackRequest(BaseModel):
    """Create evidence pack request"""

    session_id: Optional[str] = None
    sources: list[ClinicalSourceRequest]


class EvidencePackResponse(BaseModel):
    """Evidence pack response"""

    pack_id: str
    created_at: str
    session_id: Optional[str]
    source_count: int
    source_hashes: list[str]
    policy_snapshot_id: str
    metadata: dict


router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.post("/packs", response_model=EvidencePackResponse, status_code=201)
async def create_evidence_pack(request: CreateEvidencePackRequest) -> EvidencePackResponse:
    """
    Create evidence pack from clinical sources.

    **Clean Code Architecture:**
    - EvidenceService handles pack creation and storage
    - Uses DI container for dependency injection
    - AuditService logs all pack creations

    Body:
    - session_id: Optional session ID
    - sources: List of clinical sources

    Returns:
    - Evidence pack with hashes and metadata
    """
    try:
        # Get services from DI container
        evidence_service = get_container().get_evidence_service()
        audit_service = get_container().get_audit_service()

        # Convert to dictionaries
        sources_dicts = [src.model_dump() for src in request.sources]

        # Delegate to service
        result = evidence_service.create_evidence_pack(
            sources=sources_dicts,
            session_id=request.session_id,
        )

        # Log audit trail
        audit_service.log_action(
            action="evidence_pack_created",
            user_id="system",
            resource=f"evidence_pack:{result['pack_id']}",
            result="success",
            details={
                "source_count": result["source_count"],
                "session_id": request.session_id,
            },
        )

        logger.info(
            f"EVIDENCE_PACK_CREATED: pack_id={result['pack_id']}, sources={result['source_count']}"
        )

        return EvidencePackResponse(
            pack_id=result["pack_id"],
            created_at=result["created_at"],
            session_id=result["session_id"],
            source_count=result["source_count"],
            source_hashes=result["source_hashes"],
            policy_snapshot_id=result["policy_snapshot_id"],
            metadata=result["metadata"],
        )

    except ValueError as e:
        logger.warning(f"EVIDENCE_PACK_CREATION_VALIDATION_FAILED: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"EVIDENCE_PACK_CREATION_FAILED: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create evidence pack")


@router.get("/packs/{pack_id}", response_model=EvidencePackResponse)
async def get_evidence_pack(pack_id: str) -> EvidencePackResponse:
    """
    Get evidence pack by ID.

    **Clean Code Architecture:**
    - EvidenceService handles pack retrieval
    - Uses DI container for dependency injection

    Path params:
    - pack_id: Pack identifier

    Returns:
    - Evidence pack details
    """
    try:
        # Get services from DI container
        evidence_service = get_container().get_evidence_service()
        audit_service = get_container().get_audit_service()

        # Delegate to service
        result = evidence_service.get_evidence_pack(pack_id)

        if not result:
            logger.warning(f"EVIDENCE_PACK_NOT_FOUND: pack_id={pack_id}")
            raise HTTPException(status_code=404, detail=f"Pack {pack_id} not found")

        # Log audit trail
        audit_service.log_action(
            action="evidence_pack_retrieved",
            user_id="system",
            resource=f"evidence_pack:{pack_id}",
            result="success",
        )

        logger.info(f"EVIDENCE_PACK_RETRIEVED: pack_id={pack_id}")

        return EvidencePackResponse(
            pack_id=result["pack_id"],
            created_at=result["created_at"],
            session_id=result["session_id"],
            source_count=result["source_count"],
            source_hashes=result["source_hashes"],
            policy_snapshot_id=result["policy_snapshot_id"],
            metadata=result["metadata"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"EVIDENCE_PACK_RETRIEVAL_FAILED: pack_id={pack_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve evidence pack")


@router.get("/sessions/{session_id}/evidence")
async def get_session_evidence(session_id: str) -> list[EvidencePackResponse]:
    """
    Get all evidence packs for a session.

    **Clean Code Architecture:**
    - EvidenceService handles session-based filtering
    - Uses DI container for dependency injection

    Path params:
    - session_id: Session identifier

    Returns:
    - List of evidence packs for the session
    """
    try:
        # Get services from DI container
        evidence_service = get_container().get_evidence_service()
        audit_service = get_container().get_audit_service()

        # Delegate to service
        results = evidence_service.get_session_evidence(session_id)

        # Log audit trail
        audit_service.log_action(
            action="session_evidence_retrieved",
            user_id="system",
            resource=f"session:{session_id}",
            result="success",
            details={"pack_count": len(results)},
        )

        logger.info(f"SESSION_EVIDENCE_RETRIEVED: session_id={session_id}, count={len(results)}")

        return [
            EvidencePackResponse(
                pack_id=pack["pack_id"],
                created_at=pack["created_at"],
                session_id=pack["session_id"],
                source_count=pack["source_count"],
                source_hashes=pack["source_hashes"],
                policy_snapshot_id=pack["policy_snapshot_id"],
                metadata=pack["metadata"],
            )
            for pack in results
        ]

    except Exception as e:
        logger.error(f"SESSION_EVIDENCE_RETRIEVAL_FAILED: session_id={session_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session evidence")
