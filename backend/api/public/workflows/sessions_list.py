"""Lightweight Sessions List Endpoint - Direct HDF5 Read.

Simple, fast endpoint to list sessions without Timeline API overhead.
Reads directly from task-based HDF5 schema.

Author: Claude Code
Created: 2025-11-16
"""

from __future__ import annotations

import h5py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.storage.task_repository import CORPUS_PATH

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================


class SessionListItem(BaseModel):
    """Lightweight session list item."""

    session_id: str = Field(..., description="Session UUID")
    created_at: str = Field(..., description="ISO timestamp")
    has_transcription: bool = Field(default=False)
    has_diarization: bool = Field(default=False)
    has_soap: bool = Field(default=False)
    chunk_count: int = Field(default=0, description="Number of transcription chunks")
    duration_seconds: float = Field(default=0.0, description="Total duration")
    preview: str = Field(default="", description="First chunk preview (max 200 chars)")
    patient_name: str = Field(
        default="Paciente", description="Patient name (extracted from dialogue or default)"
    )
    doctor_name: str = Field(default="", description="Doctor name (extracted from dialogue)")


class SessionsListResponse(BaseModel):
    """Response for sessions list."""

    sessions: list[SessionListItem] = Field(default_factory=list, description="List of sessions")
    total: int = Field(..., description="Total number of sessions")


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/sessions",
    response_model=SessionsListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
) -> SessionsListResponse:
    """List sessions from HDF5 (lightweight, fast).

    Direct read from /sessions/{id}/tasks/ structure.
    Much faster than Timeline API for simple listing.

    Args:
        limit: Maximum number of sessions to return (default 20)
        offset: Number of sessions to skip (default 0)

    Returns:
        SessionsListResponse with session list
    """
    try:
        logger.info("SESSIONS_LIST_STARTED", limit=limit, offset=offset)

        sessions_list: list[SessionListItem] = []

        with h5py.File(CORPUS_PATH, "r") as f:
            if "sessions" not in f:
                logger.warning("NO_SESSIONS_GROUP_IN_HDF5")
                return SessionsListResponse(sessions=[], total=0)

            sessions_group = f["sessions"]
            all_session_ids = list(sessions_group.keys())

            # Sort by creation time (newest first)
            # Read metadata quickly to get timestamps
            session_metadata_list = []
            for session_id in all_session_ids:
                try:
                    session_group = sessions_group[session_id]
                    if "tasks" not in session_group:  # type: ignore[operator]
                        continue

                    # Get created_at from TRANSCRIPTION task metadata or first chunk
                    tasks = session_group["tasks"]
                    created_at = None

                    if "TRANSCRIPTION" in tasks:  # type: ignore[operator]
                        # Try metadata first
                        if "metadata" in tasks["TRANSCRIPTION"]:  # type: ignore[operator]
                            meta_ds = tasks["TRANSCRIPTION"]["metadata"]
                            if isinstance(meta_ds, h5py.Dataset):
                                meta_json = meta_ds[()].decode("utf-8")
                                import json

                                meta = json.loads(meta_json)
                                created_at = meta.get("created_at")

                        # Fallback: get created_at from first chunk (chunk_0)
                        if not created_at and "chunks" in tasks["TRANSCRIPTION"]:  # type: ignore[operator]
                            chunks_group = tasks["TRANSCRIPTION"]["chunks"]
                            if "chunk_0" in chunks_group:  # type: ignore[operator]
                                chunk_0 = chunks_group["chunk_0"]
                                if "created_at" in chunk_0:  # type: ignore[operator]
                                    created_at_ds = chunk_0["created_at"]
                                    if isinstance(created_at_ds, h5py.Dataset):
                                        created_at = created_at_ds[()].decode("utf-8")

                    # Last resort: use session_id timestamp if it has one (UUIDs don't have timestamps)
                    if not created_at:
                        # Use a very old date so it appears at the bottom
                        created_at = "2000-01-01T00:00:00+00:00"

                    session_metadata_list.append((session_id, created_at))
                except Exception as e:
                    logger.warning("SKIP_SESSION_METADATA", session_id=session_id, error=str(e))
                    continue

            # Sort by created_at (newest first)
            session_metadata_list.sort(key=lambda x: x[1], reverse=True)

            # Apply pagination
            paginated_sessions = session_metadata_list[offset : offset + limit]

            # Read detailed data for paginated sessions
            for session_id, created_at in paginated_sessions:
                try:
                    session_group = sessions_group[session_id]
                    if "tasks" not in session_group:  # type: ignore[operator]
                        continue

                    tasks = session_group["tasks"]

                    # Check which tasks exist
                    has_transcription = "TRANSCRIPTION" in tasks  # type: ignore[operator]
                    has_diarization = "DIARIZATION" in tasks  # type: ignore[operator]
                    has_soap = "SOAP_GENERATION" in tasks  # type: ignore[operator]

                    chunk_count = 0
                    duration_seconds = 0.0
                    preview = ""

                    # Get transcription details
                    if has_transcription:
                        trans_task = tasks["TRANSCRIPTION"]
                        if "chunks" in trans_task:  # type: ignore[operator]
                            chunk_count = len(trans_task["chunks"].keys())

                            # Get first chunk for preview
                            if chunk_count > 0:
                                try:
                                    chunk_0 = trans_task["chunks"]["chunk_0"]
                                    if "transcript" in chunk_0:  # type: ignore[operator]
                                        transcript_ds = chunk_0["transcript"]
                                        if isinstance(transcript_ds, h5py.Dataset):
                                            transcript = transcript_ds[()].decode("utf-8")
                                            preview = transcript[:200]  # Max 200 chars

                                    if "duration" in chunk_0:  # type: ignore[operator]
                                        # Sum all chunk durations (rough estimate)
                                        for i in range(chunk_count):
                                            chunk_key = f"chunk_{i}"
                                            if chunk_key in trans_task["chunks"]:  # type: ignore[operator]
                                                chunk = trans_task["chunks"][chunk_key]
                                                if "duration" in chunk:  # type: ignore[operator]
                                                    duration_seconds += float(chunk["duration"][()])
                                except Exception as e:
                                    logger.warning(
                                        "SKIP_CHUNK_DATA",
                                        session_id=session_id,
                                        error=str(e),
                                    )

                    # Extract patient and doctor names from session metadata or diarization
                    patient_name = "Paciente"
                    doctor_name = ""

                    # First, try to get from session attributes (preferred)
                    if hasattr(session_group, "attrs"):
                        patient_name = session_group.attrs.get("patient_name", "Paciente")
                        if not doctor_name and "doctor_name" in session_group.attrs:
                            doctor_name = session_group.attrs.get("doctor_name", "")

                    # Fallback: extract from diarization dialogue
                    if has_diarization and (patient_name == "Paciente" or not doctor_name):
                        try:
                            diar_task = tasks["DIARIZATION"]
                            if "segments" in diar_task:  # type: ignore[operator]
                                segments = diar_task["segments"]

                                # Check first few segments for doctor name
                                for seg_key in list(segments.keys())[:5]:  # Check first 5 segments
                                    segment = segments[seg_key]
                                    if "text" in segment:  # type: ignore[operator]
                                        text_ds = segment["text"]
                                        if isinstance(text_ds, h5py.Dataset):
                                            text = text_ds[()].decode("utf-8").lower()

                                            # Look for "doctor [name]" or "doctora [name]" or "soy el doctor [name]"
                                            import re

                                            # Try multiple patterns (most specific first)
                                            patterns = [
                                                r"(?:soy el|mi nombre es|me llamo)\s+doctor[a]?\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]+)",
                                                r"doctor[a]?\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]{3,})",  # At least 3 chars to avoid "Lo"
                                            ]

                                            for pattern in patterns:
                                                doctor_match = re.search(
                                                    pattern, text, re.IGNORECASE
                                                )
                                                if doctor_match:
                                                    name = doctor_match.group(1).capitalize()
                                                    # Filter out common words that aren't names
                                                    if name.lower() not in [
                                                        "que",
                                                        "como",
                                                        "por",
                                                        "con",
                                                        "para",
                                                        "los",
                                                        "las",
                                                        "del",
                                                        "una",
                                                        "uno",
                                                    ]:
                                                        doctor_name = name
                                                        break

                                            if doctor_name:
                                                break
                        except Exception as e:
                            logger.warning(
                                "SKIP_NAME_EXTRACTION", session_id=session_id, error=str(e)
                            )

                    sessions_list.append(
                        SessionListItem(
                            session_id=session_id,
                            created_at=created_at,
                            has_transcription=has_transcription,
                            has_diarization=has_diarization,
                            has_soap=has_soap,
                            chunk_count=chunk_count,
                            duration_seconds=duration_seconds,
                            preview=preview,
                            patient_name=patient_name,
                            doctor_name=doctor_name,
                        )
                    )

                except Exception as e:
                    logger.warning("SKIP_SESSION_DETAILS", session_id=session_id, error=str(e))
                    continue

        logger.info(
            "SESSIONS_LIST_SUCCESS",
            total=len(all_session_ids),
            returned=len(sessions_list),
        )

        return SessionsListResponse(sessions=sessions_list, total=len(all_session_ids))

    except Exception as e:
        logger.error("SESSIONS_LIST_FAILED", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {e!s}",
        ) from e
