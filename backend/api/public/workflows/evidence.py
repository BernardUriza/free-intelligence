"""Evidence Pack Workflow Endpoints.

PUBLIC layer endpoints for evidence pack management:
- GET /sessions/{session_id}/evidence → Get evidence pack (auto-generate if not exists)

Architecture:
  PUBLIC (this file) → SERVICE → REPOSITORY → HDF5

Author: Bernard Uriza Orozco
Created: 2025-11-17 (Evidence Pack Auto-Generation)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/sessions/{session_id}/evidence",
    status_code=status.HTTP_200_OK,
)
async def get_evidence_pack_workflow(session_id: str) -> dict:
    """Get evidence pack for session - generates if not exists (PUBLIC endpoint).

    Args:
        session_id: Session UUID

    Returns:
        Evidence pack with sources, citations, and metadata

    Raises:
        500: Failed to load or generate evidence pack
    """
    try:
        logger.info("EVIDENCE_PACK_GET_STARTED", session_id=session_id)

        # Try to find existing evidence pack for this session
        # Pack IDs follow pattern: pack_{timestamp}_{session_id_suffix}
        # For now, we'll generate if not found
        try:
            # TODO: Implement session_id -> pack_id mapping in HDF5
            # For now, generate a new pack if not found
            logger.info("EVIDENCE_PACK_NOT_FOUND_GENERATING", session_id=session_id)

            # Generate evidence pack from session data
            pack_data = await generate_evidence_pack_from_session(session_id)

            logger.info("EVIDENCE_PACK_GENERATED_SUCCESS", session_id=session_id)

            return {
                "session_id": session_id,
                "evidence_pack": pack_data,
            }

        except ValueError as e:
            # Evidence pack doesn't exist and couldn't be generated
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
        logger.error(
            "EVIDENCE_PACK_GET_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evidence pack: {e!s}",
        ) from e


async def generate_evidence_pack_from_session(session_id: str) -> dict:
    """Generate evidence pack from session data (SOAP, diarization, etc).

    Args:
        session_id: Session identifier

    Returns:
        Evidence pack dictionary

    Raises:
        ValueError: If session has insufficient data for evidence pack
    """
    from backend.compat import UTC, datetime

    from backend.models.task_type import TaskType
    from backend.storage.task_repository import (
        get_diarization_segments,
        get_soap_data,
        task_exists,
    )

    # Check if SOAP exists (required for evidence pack)
    if not task_exists(session_id, TaskType.SOAP_GENERATION):
        raise ValueError(f"SOAP not found for session {session_id}. Generate SOAP first.")

    # Get SOAP data
    soap_data = get_soap_data(session_id)

    # Get diarization segments if available
    sources = []
    if task_exists(session_id, TaskType.DIARIZATION):
        segments = get_diarization_segments(session_id)

        # Create source from diarization
        sources.append(
            {
                "source_id": f"diarization_{session_id[:8]}",
                "tipo_doc": "transcripcion_audio",
                "fecha": datetime.now(UTC).isoformat(),
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
            "fecha": datetime.now(UTC).isoformat(),
            "paciente_id": session_id,
            "hallazgo": soap_data.get("assessment", {}).get("primary_diagnosis", "N/A"),
            "severidad": "moderada",  # Default severity
            "raw_text": soap_text,
        }
    )

    # Generate source hashes (SHA-256 of raw_text)
    import hashlib

    source_hashes = [
        hashlib.sha256(src.get("raw_text", "").encode()).hexdigest() for src in sources
    ]

    pack_data = {
        "pack_id": f"pack_{int(datetime.now(UTC).timestamp())}_{session_id[:8]}",
        "created_at": datetime.now(UTC).isoformat(),
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
