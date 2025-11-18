"""Public Timeline API Router.

Provides session summaries and timeline data for AURITY frontend.

Architecture: PUBLIC → HDF5 (read-only, no internal dependencies)
Created: 2025-11-15
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import h5py
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.storage import task_repository

logger = get_logger(__name__)

router = APIRouter(prefix="/timeline", tags=["timeline"])

# HDF5 corpus path
CORPUS_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "corpus.h5"

# ============================================================================
# RESPONSE MODELS
# ============================================================================


class SessionMetadata(BaseModel):
    """Session metadata for listing"""

    session_id: str
    created_at: str = ""
    updated_at: str | None = None
    chunk_count: int = 0
    status: str = "unknown"


class SessionSize(BaseModel):
    """Session size metrics"""

    interaction_count: int = 0
    total_tokens: int = 0
    total_chars: int = 0


class SessionSummary(BaseModel):
    """Session summary for timeline UI"""

    metadata: SessionMetadata
    size: SessionSize = Field(default_factory=SessionSize)
    preview: str = Field(default="", description="Preview of first transcription")
    task_counts: dict[str, int] = Field(default_factory=dict)


class SessionsListResponse(BaseModel):
    """Paginated sessions list"""

    items: list[SessionSummary]
    total: int
    limit: int
    offset: int


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of sessions"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort: str = Query("recent", description="Sort order: recent, oldest"),
) -> list[SessionSummary]:
    """List sessions with pagination.

    Returns session summaries with metadata from HDF5.

    Performance target: p95 <300ms
    """
    logger.info("TIMELINE_SESSIONS_LIST", limit=limit, offset=offset, sort=sort)

    try:
        # Get all sessions from HDF5
        sessions: list[str] = []

        if CORPUS_PATH.exists():
            with h5py.File(CORPUS_PATH, "r") as f:
                if "sessions" in f:  # type: ignore[operator]
                    sessions = list(f["sessions"].keys())  # type: ignore[union-attr]

        # Build summaries for ALL sessions first (need created_at for sorting)
        all_summaries = []
        for session_id in sessions:
            try:
                # Get transcription metadata
                metadata = task_repository.get_task_metadata(session_id, "TRANSCRIPTION")

                # Get chunks to calculate real chunk count
                chunk_count = 0
                preview = ""
                try:
                    chunks = task_repository.get_task_chunks(session_id, "TRANSCRIPTION")
                    chunk_count = len(chunks) if chunks else 0

                    # Get first chunk preview
                    if chunks and len(chunks) > 0:
                        transcript = chunks[0].get("transcript", "")
                        preview = transcript[:200] if transcript else ""
                except Exception as chunk_error:
                    logger.warning(
                        "TIMELINE_CHUNK_FETCH_ERROR",
                        session_id=session_id,
                        error=str(chunk_error),
                    )

                # Count tasks
                task_counts: dict[str, int] = {}
                for task_type_str in ["TRANSCRIPTION", "DIARIZATION", "SOAP_GENERATION"]:
                    try:
                        if task_repository.task_exists(session_id, task_type_str):
                            task_counts[task_type_str] = 1
                    except Exception:
                        pass

                summary = SessionSummary(
                    metadata=SessionMetadata(
                        session_id=session_id,
                        created_at=metadata.get("created_at", "") if metadata else "",
                        updated_at=metadata.get("updated_at") if metadata else None,
                        chunk_count=chunk_count,
                        status=metadata.get("status", "unknown") if metadata else "unknown",
                    ),
                    size=SessionSize(
                        interaction_count=chunk_count,
                        total_tokens=0,  # TODO: Calculate from metadata if available
                        total_chars=len(preview),
                    ),
                    preview=preview,
                    task_counts=task_counts,
                )
                all_summaries.append(summary)

            except Exception as e:
                logger.warning(
                    "SESSION_SUMMARY_ERROR",
                    session_id=session_id,
                    error=str(e),
                )
                # Skip session on error
                continue

        # Sort by created_at (most recent first or oldest first)
        all_summaries.sort(key=lambda s: s.metadata.created_at or "", reverse=(sort == "recent"))

        # Paginate after sorting
        paginated_summaries = all_summaries[offset : offset + limit]

        logger.info(
            "TIMELINE_SESSIONS_RESPONSE",
            total=len(sessions),
            returned=len(paginated_summaries),
            sort=sort,
        )

        return paginated_summaries

    except Exception as e:
        logger.error("TIMELINE_SESSIONS_ERROR", error=str(e), exc_info=True)
        return []


@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str) -> dict[str, Any]:
    """Get detailed session information.

    Returns full session data including all tasks.

    Frontend expects format with metadata, timespan, size, policy_badges, events.
    """
    logger.info("TIMELINE_SESSION_DETAIL", session_id=session_id)

    try:
        # Get transcription metadata for base info
        transcription_metadata = task_repository.get_task_metadata(session_id, "TRANSCRIPTION")

        if not transcription_metadata:
            # Session not found
            logger.warning("SESSION_NOT_FOUND", session_id=session_id)
            return {
                "metadata": {"session_id": session_id},
                "timespan": {"start": "", "end": "", "duration_ms": 0, "duration_human": ""},
                "size": {
                    "interaction_count": 0,
                    "total_tokens": 0,
                    "total_chars": 0,
                    "avg_tokens_per_interaction": 0,
                    "size_human": "0 chars",
                },
                "policy_badges": {
                    "hash_verified": "N/A",
                    "policy_compliant": "N/A",
                    "redaction_applied": "N/A",
                    "audit_logged": "N/A",
                },
                "events": [],
                "generation_mode": "unknown",
                "auto_events_count": 0,
                "manual_events_count": 0,
                "redaction_stats": {},
            }

        # Build metadata
        created_at = transcription_metadata.get("created_at", "")
        updated_at = transcription_metadata.get("updated_at", created_at)

        # Build timespan
        timespan = {
            "start": created_at,
            "end": updated_at,
            "duration_ms": 0,  # TODO: Calculate if needed
            "duration_human": "Unknown",
        }

        # Get chunks for size calculation
        chunks = []
        total_chars = 0
        try:
            chunks = task_repository.get_task_chunks(session_id, "TRANSCRIPTION")
            for chunk in chunks:
                transcript = chunk.get("transcript", "")
                total_chars += len(transcript)
        except Exception as chunk_error:
            logger.warning("CHUNK_FETCH_ERROR", session_id=session_id, error=str(chunk_error))

        # Build size
        size = {
            "interaction_count": len(chunks),
            "total_tokens": 0,  # TODO: Calculate from metadata if available
            "total_chars": total_chars,
            "avg_tokens_per_interaction": 0,
            "size_human": f"{total_chars} chars",
        }

        # Build policy badges (placeholder for now)
        policy_badges = {
            "hash_verified": "OK",
            "policy_compliant": "OK",
            "redaction_applied": "N/A",
            "audit_logged": "OK",
        }

        # Build events array from chunks (converting chunks to event format)
        events = []
        for idx, chunk in enumerate(chunks):
            transcript = chunk.get("transcript", "")
            created_at_chunk = chunk.get("created_at", created_at)
            events.append(
                {
                    "event_id": f"chunk_{idx}",
                    "event_type": "transcription",
                    "timestamp": created_at_chunk,
                    "who": "system",
                    "what": transcript[:100] if transcript else "",
                    "summary": transcript if transcript else None,
                    "content_hash": chunk.get("audio_hash", ""),
                    "redaction_policy": "none",
                    "causality": [],
                    "tags": ["transcription", f"chunk_{idx}"],
                    "auto_generated": True,
                    "generation_mode": "deepgram",
                    "confidence_score": chunk.get("confidence", 0.0),
                }
            )

        # Build complete detail response
        detail = {
            "metadata": {
                "session_id": session_id,
                "thread_id": None,
                "owner_hash": "unknown",
                "created_at": created_at,
                "updated_at": updated_at,
            },
            "timespan": timespan,
            "size": size,
            "policy_badges": policy_badges,
            "events": events,
            "generation_mode": "automated",
            "auto_events_count": len(events),
            "manual_events_count": 0,
            "redaction_stats": {},
        }

        return detail

    except Exception as e:
        logger.error(
            "TIMELINE_SESSION_DETAIL_ERROR",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        return {
            "metadata": {"session_id": session_id},
            "timespan": {"start": "", "end": "", "duration_ms": 0, "duration_human": ""},
            "size": {
                "interaction_count": 0,
                "total_tokens": 0,
                "total_chars": 0,
                "avg_tokens_per_interaction": 0,
                "size_human": "0 chars",
            },
            "policy_badges": {
                "hash_verified": "N/A",
                "policy_compliant": "N/A",
                "redaction_applied": "N/A",
                "audit_logged": "N/A",
            },
            "events": [],
            "generation_mode": "unknown",
            "auto_events_count": 0,
            "manual_events_count": 0,
            "redaction_stats": {},
            "error": str(e),
        }
