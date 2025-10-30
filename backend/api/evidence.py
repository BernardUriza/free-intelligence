#!/usr/bin/env python3
"""
Free Intelligence - Evidence API

FastAPI router for evidence packs.

File: backend/api/evidence.py
Card: FI-DATA-RES-021
Created: 2025-10-30
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.evidence_pack import (
    ClinicalSource,
    EvidencePackBuilder,
    create_evidence_pack_from_sources,
)

# ============================================================================
# PYDANTIC MODELS
# ============================================================================


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
    sources: List[ClinicalSourceRequest]


class EvidencePackResponse(BaseModel):
    """Evidence pack response"""

    pack_id: str
    created_at: str
    session_id: Optional[str]
    source_count: int
    source_hashes: List[str]
    policy_snapshot_id: str
    metadata: Dict


# ============================================================================
# FASTAPI ROUTER
# ============================================================================

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

# In-memory store for demo (replace with persistent storage)
evidence_store: Dict[str, Dict] = {}


@router.post("/packs", response_model=EvidencePackResponse, status_code=201)
async def create_evidence_pack(request: CreateEvidencePackRequest):
    """
    Create evidence pack from clinical sources.

    Body:
    - session_id: Optional session ID
    - sources: List of clinical sources

    Returns:
    - Evidence pack with hashes
    """
    if not request.sources:
        raise HTTPException(status_code=400, detail="No sources provided")

    # Convert to dictionaries
    sources_dicts = [src.dict() for src in request.sources]

    # Create pack
    pack = create_evidence_pack_from_sources(
        sources_dicts, session_id=request.session_id
    )

    # Store pack
    builder = EvidencePackBuilder()
    pack_dict = builder.to_dict(pack)
    evidence_store[pack.pack_id] = pack_dict

    # Return response
    return EvidencePackResponse(
        pack_id=pack.pack_id,
        created_at=pack.created_at,
        session_id=pack.session_id,
        source_count=len(pack.sources),
        source_hashes=pack.source_hashes,
        policy_snapshot_id=pack.policy_snapshot_id,
        metadata=pack.metadata,
    )


@router.get("/packs/{pack_id}", response_model=EvidencePackResponse)
async def get_evidence_pack(pack_id: str):
    """
    Get evidence pack by ID.

    Path params:
    - pack_id: Pack identifier

    Returns:
    - Evidence pack details
    """
    if pack_id not in evidence_store:
        raise HTTPException(status_code=404, detail=f"Pack {pack_id} not found")

    pack_dict = evidence_store[pack_id]

    return EvidencePackResponse(
        pack_id=pack_dict["pack_id"],
        created_at=pack_dict["created_at"],
        session_id=pack_dict["session_id"],
        source_count=pack_dict["metadata"]["source_count"],
        source_hashes=pack_dict["source_hashes"],
        policy_snapshot_id=pack_dict["policy_snapshot_id"],
        metadata=pack_dict["metadata"],
    )


@router.get("/sessions/{session_id}/evidence")
async def get_session_evidence(session_id: str):
    """
    Get all evidence packs for a session.

    Path params:
    - session_id: Session identifier

    Returns:
    - List of evidence packs
    """
    # Filter packs by session_id
    session_packs = [
        pack for pack in evidence_store.values() if pack.get("session_id") == session_id
    ]

    if not session_packs:
        return []

    return [
        EvidencePackResponse(
            pack_id=pack["pack_id"],
            created_at=pack["created_at"],
            session_id=pack["session_id"],
            source_count=pack["metadata"]["source_count"],
            source_hashes=pack["source_hashes"],
            policy_snapshot_id=pack["policy_snapshot_id"],
            metadata=pack["metadata"],
        )
        for pack in session_packs
    ]
