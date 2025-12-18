from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.public.workflows.models import (
    DoctorFeedbackRequest,
    DoctorFeedbackResponse,
)
from backend.logger import get_logger
from backend.src.fi_auth import User, get_current_user
from backend.validators import validate_session_id

router = APIRouter()
logger = get_logger(__name__)


@router.get("/sessions/{session_id}/audit")
async def get_session_audit(session_id: str) -> dict[str, Any]:
    """Get complete audit data for doctor review."""
    validate_session_id(session_id)

    from backend.models.task_type import TaskType
    from backend.src.fi_storage.infrastructure.hdf5.task_repository import (
        get_diarization_segments,
        get_session_metadata,
        get_soap_data,
        get_task_metadata,
    )

    try:
        logger.info("SESSION_AUDIT_GET_START", session_id=session_id)

        session_meta = get_session_metadata(session_id)
        if not session_meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {session_id} not found"
            )

        soap_data = get_soap_data(session_id)
        soap_task_meta = get_task_metadata(session_id, TaskType.SOAP_GENERATION)
        diarization_segments = get_diarization_segments(session_id)

        flags = _analyze_session_flags(soap_data, soap_task_meta)
        doctor_feedback = session_meta.get("doctor_feedback")

        response = {
            "session_id": session_id,
            "patient": session_meta.get("patient", {}),
            "session_metadata": {
                "date": session_meta.get("created_at"),
                "duration_seconds": session_meta.get("duration_seconds"),
                "doctor": session_meta.get("doctor_name", "Unknown"),
                "status": session_meta.get("audit_status", "pending_review"),
            },
            "orchestration": {
                "strategy": (
                    soap_task_meta.get("orchestration_strategy", "UNKNOWN")
                    if soap_task_meta
                    else "UNKNOWN"
                ),
                "personas_invoked": (
                    soap_task_meta.get("personas_invoked", []) if soap_task_meta else []
                ),
                "confidence_score": (
                    soap_task_meta.get("confidence_score", 0.0) if soap_task_meta else 0.0
                ),
                "complexity_score": (
                    soap_task_meta.get("complexity_score", 0.0) if soap_task_meta else 0.0
                ),
                "steps": (soap_task_meta.get("intermediate_outputs", []) if soap_task_meta else []),
            },
            "soap_note": soap_data or {},
            "diarization": {"segments": diarization_segments or []},
            "flags": flags,
            "doctor_feedback": doctor_feedback,
        }

        logger.info(
            "SESSION_AUDIT_GET_SUCCESS",
            session_id=session_id,
            flags_count=len(flags),
            has_feedback=doctor_feedback is not None,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("SESSION_AUDIT_GET_FAILED", session_id=session_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session audit: {e!s}",
        ) from e


def _analyze_session_flags(
    soap_data: dict[str, Any] | None,
    orchestration: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Analyze session for potential issues requiring doctor attention."""
    flags: list[dict[str, Any]] = []

    if not soap_data or not orchestration:
        return flags

    confidence = orchestration.get("confidence_score", 1.0)
    if confidence < 0.95:
        flags.append(
            {
                "type": "low_confidence",
                "severity": "warning",
                "message": f"Confidence score below 95% ({confidence:.0%})",
                "location": "overall",
            }
        )

    plan = soap_data.get("plan", {})
    medications = plan.get("medications", [])

    has_enalapril = any(
        "enalapril" in med.get("name", "").lower() for med in medications if isinstance(med, dict)
    )
    has_losartan = any(
        "losartán" in med.get("name", "").lower() or "losartan" in med.get("name", "").lower()
        for med in medications
        if isinstance(med, dict)
    )

    if has_enalapril and has_losartan:
        flags.append(
            {
                "type": "medication_interaction",
                "severity": "critical",
                "message": "Posible interacción: Enalapril + Losartán (ambos IECA)",
                "location": "plan.medications",
            }
        )

    objective = soap_data.get("objective")
    if not objective or (isinstance(objective, str) and len(objective.strip()) < 10):
        flags.append(
            {
                "type": "missing_objective_data",
                "severity": "warning",
                "message": "No se registraron signos vitales ni exploración física",
                "location": "objective",
            }
        )

    complexity = orchestration.get("complexity_score", 0.0)
    if complexity >= 60 and confidence < 0.90:
        flags.append(
            {
                "type": "complex_low_confidence",
                "severity": "warning",
                "message": f"Caso complejo (score {complexity:.1f}) con confianza baja ({confidence:.0%})",
                "location": "overall",
            }
        )

    return flags


@router.post("/sessions/{session_id}/feedback")
async def submit_doctor_feedback(
    session_id: str,
    feedback: DoctorFeedbackRequest,
    current_user: User | None = Depends(get_current_user),
) -> DoctorFeedbackResponse:
    """Submit doctor's audit feedback for a session."""
    from backend.api.public.workflows.models import DoctorFeedbackResponse
    from backend.src.fi_storage.infrastructure.hdf5.task_repository import (
        get_soap_data,
        save_soap_data,
        update_session_metadata,
    )

    try:
        logger.info(
            "DOCTOR_FEEDBACK_SUBMIT_START",
            session_id=session_id,
            decision=feedback.decision,
            rating=feedback.rating,
            corrections_count=len(feedback.corrections),
        )

        if current_user:
            user_identifier = current_user.user_id or current_user.email or "unknown"
            user_display_name = (
                current_user.name
                or current_user.email
                or (f"User {current_user.user_id[:8]}" if current_user.user_id else "Unknown User")
            )
        else:
            logger.warning(
                "AUTH_CONTEXT_MISSING",
                session_id=session_id,
                message="No authenticated user - using 'system' identifier",
            )
            user_identifier = "system"
            user_display_name = "System"

        feedback_data = {
            "rating": feedback.rating,
            "comments": feedback.comments,
            "corrections": [corr.dict() for corr in feedback.corrections],
            "decision": feedback.decision,
            "submitted_at": __import__("datetime")
            .datetime.now(__import__("datetime").UTC)
            .isoformat(),
            "submitted_by": user_identifier,
            "submitted_by_display": user_display_name,
        }

        update_session_metadata(
            session_id,
            {
                "doctor_feedback": feedback_data,
                "audit_status": feedback.decision,
                "audit_rating": feedback.rating,
                "audited_at": __import__("datetime")
                .datetime.now(__import__("datetime").UTC)
                .isoformat(),
                "audited_by": user_identifier,
                "audited_by_display": user_display_name,
            },
        )

        corrections_applied = 0
        if feedback.corrections:
            soap_data = get_soap_data(session_id)
            if soap_data:
                for correction in feedback.corrections:
                    section = correction.section
                    if section in soap_data:
                        if isinstance(soap_data[section], str):
                            soap_data[section] = soap_data[section].replace(
                                correction.original,
                                correction.corrected,
                            )
                            corrections_applied += 1
                        elif isinstance(soap_data[section], dict):
                            if "corrections" not in soap_data[section]:
                                soap_data[section]["corrections"] = []
                            soap_data[section]["corrections"].append(correction.dict())
                            corrections_applied += 1

                save_soap_data(session_id, soap_data, TaskType.SOAP_GENERATION)

        logger.info(
            "DOCTOR_FEEDBACK_SUBMITTED",
            session_id=session_id,
            decision=feedback.decision,
            rating=feedback.rating,
            corrections_applied=corrections_applied,
        )

        return DoctorFeedbackResponse(
            status="feedback_saved",
            session_id=session_id,
            audit_status=feedback.decision,
            corrections_applied=corrections_applied,
        )

    except Exception as e:
        logger.error(
            "DOCTOR_FEEDBACK_SUBMIT_FAILED", session_id=session_id, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit doctor feedback: {e!s}",
        ) from e
