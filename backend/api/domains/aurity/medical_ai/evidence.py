"""Evidence Pack Workflow Endpoints.

Generates evidence packs from session data (SOAP, diarization).
Auto-generates if not exists.

Endpoints (1 total):
- GET /sessions/{session_id}/evidence - Get/generate evidence pack

Author: Bernard Uriza Orozco
Created: 2025-11-17 (Evidence Pack Auto-Generation)
Migrated: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.infrastructure.auth import User, get_current_user, validate_session_access
from backend.models.task_type import TaskType
from backend.repositories.interfaces import ITaskRepository
from backend.infrastructure.common.repository_singletons import get_task_repository
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================


async def _generate_evidence_pack_from_session(
    session_id: str,
    task_repo: ITaskRepository,
) -> dict:
    """Generate evidence pack from session data (SOAP, diarization).

    Args:
        session_id: Session identifier
        task_repo: Task repository (injected)

    Returns:
        Evidence pack dictionary

    Raises:
        ValueError: If session has insufficient data for evidence pack
    """
    # Check if SOAP exists (required for evidence pack)
    if not task_repo.task_exists(session_id, TaskType.SOAP_GENERATION):
        raise ValueError(f"SOAP not found for session {session_id}. Generate SOAP first.")

    # Get SOAP data
    soap_data = task_repo.get_soap_data(session_id)

    # Get diarization segments if available
    sources = []
    if task_repo.task_exists(session_id, TaskType.DIARIZATION):
        segments = task_repo.get_diarization_segments(session_id)

        sources.append(
            {
                "source_id": f"diarization_{session_id[:8]}",
                "tipo_doc": "transcripcion_audio",
                "fecha": datetime.now(timezone.utc).isoformat(),
                "paciente_id": session_id,
                "hallazgo": f"Conversación médica con {len(segments)} segmentos",
                "severidad": "informativo",
                "raw_text": " ".join(seg.get("text", "") for seg in segments),
            }
        )

    # Create source from SOAP
    soap_text = f"""
Chief Complaint: {soap_data.get("subjective", {}).get("chief_complaint", "N/A")}
History: {soap_data.get("subjective", {}).get("history_present_illness", "N/A")}
Physical Exam: {soap_data.get("objective", {}).get("physical_exam", "N/A")}
Assessment: {soap_data.get("assessment", {}).get("primary_diagnosis", "N/A")}
Plan: {soap_data.get("plan", {}).get("treatment", "N/A")}
    """.strip()

    sources.append(
        {
            "source_id": f"soap_{session_id[:8]}",
            "tipo_doc": "clinical_note",
            "fecha": datetime.now(timezone.utc).isoformat(),
            "paciente_id": session_id,
            "hallazgo": soap_data.get("assessment", {}).get("primary_diagnosis", "N/A"),
            "severidad": "moderada",
            "raw_text": soap_text,
        }
    )

    # Generate source hashes (SHA-256 of raw_text)
    source_hashes = [
        hashlib.sha256(src.get("raw_text", "").encode()).hexdigest() for src in sources
    ]

    pack_data = {
        "pack_id": f"pack_{int(datetime.now(timezone.utc).timestamp())}_{session_id[:8]}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "sources": sources,
        "source_hashes": source_hashes,
        "policy_snapshot_id": "default_policy",
        "citations": [],
        "consulta": "Evidencia clínica de la sesión",
        "response": f"Evidence pack generado con {len(sources)} fuentes clínicas.",
    }

    logger.info(
        "EVIDENCE_PACK_GENERATED",
        session_id=session_id,
        source_count=len(sources),
        pack_id=pack_data["pack_id"],
    )

    return pack_data


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/sessions/{session_id}/evidence",
    status_code=status.HTTP_200_OK,
)
async def get_evidence_pack_workflow(
    session_id: str,
    task_repo: ITaskRepository = Depends(get_task_repository),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get evidence pack for session - generates if not exists.

    Args:
        session_id: Session UUID
        task_repo: Task repository (injected)
        audit_service: Audit logging service
        current_user: Authenticated user

    Returns:
        Evidence pack with sources, citations, and metadata

    Raises:
        HTTPException: 403 if access denied
        HTTPException: 500 if generation fails
    """
    validate_session_access(session_id, current_user, action="view evidence pack")

    try:
        logger.info("EVIDENCE_PACK_GET_STARTED", session_id=session_id)

        try:
            logger.info("EVIDENCE_PACK_NOT_FOUND_GENERATING", session_id=session_id)

            pack_data = await _generate_evidence_pack_from_session(session_id, task_repo)

            logger.info("EVIDENCE_PACK_GENERATED_SUCCESS", session_id=session_id)

            return {
                "session_id": session_id,
                "evidence_pack": pack_data,
            }

        except ValueError as e:
            logger.warning(
                "EVIDENCE_PACK_GENERATION_FAILED",
                session_id=session_id,
                error=str(e),
            )
            # Return empty evidence pack structure
            return {
                "session_id": session_id,
                "evidence_pack": {
                    "pack_id": f"pack_{session_id[:8]}",
                    "created_at": "",
                    "sources": [],
                    "source_hashes": [],
                    "citations": [],
                    "consulta": "",
                    "response": "No hay evidencia disponible para esta sesión aún.",
                },
            }

    except Exception as e:
        audit_service.log_action(
            action="evidence_pack_get_failed",
            user_id=current_user.id,
            resource=f"session:{session_id}",
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evidence pack: {e!s}",
        ) from e
