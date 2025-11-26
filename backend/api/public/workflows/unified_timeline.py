"""Unified Timeline API - Memoria Longitudinal Unificada.

Single endpoint that combines:
- Chat messages (from conversation memory)
- Audio transcriptions (from sessions HDF5)

All sorted chronologically with pagination and time range filters.

Philosophy: "No existen sesiones. Solo una conversación infinita."

Author: Claude Code
Created: 2025-11-22
Card: FI-PHIL-DOC-014
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

import h5py
from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.services.llm.conversation_memory import get_memory_manager
from backend.storage.task_repository import CORPUS_PATH

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Configuration (no hardcoding)
# ============================================================================

class TimelineConfig:
    """Centralized configuration for timeline limits."""

    DEFAULT_LIMIT: int = 50
    MAX_LIMIT: int = 200
    DEFAULT_WINDOW_HOURS: int = 24 * 7  # 1 week default
    MAX_WINDOW_DAYS: int = 365  # 1 year max


# ============================================================================
# Types
# ============================================================================


class EventType(str, Enum):
    """Event types for filtering."""

    ALL = "all"
    CHAT = "chat"
    AUDIO = "audio"


class UnifiedEvent(BaseModel):
    """Single event in the unified timeline."""

    id: str = Field(..., description="Unique event ID")
    timestamp: int = Field(..., description="Unix timestamp (seconds)")
    event_type: Literal["chat_user", "chat_assistant", "transcription"] = Field(
        ..., description="Type of event"
    )
    content: str = Field(..., description="Event content/text")
    source: Literal["chat", "audio"] = Field(..., description="Data source")

    # Optional metadata (all default to None)
    session_id: str | None = Field(default=None, description="Session ID if applicable")
    persona: str | None = Field(default=None, description="AI persona (for assistant messages)")
    chunk_number: int | None = Field(default=None, description="Audio chunk number")
    duration: float | None = Field(default=None, description="Audio duration in seconds")
    confidence: float | None = Field(default=None, description="Transcription confidence")
    language: str | None = Field(default=None, description="Detected language")
    stt_provider: str | None = Field(default=None, description="STT provider used")


class UnifiedTimelineResponse(BaseModel):
    """Response for unified timeline endpoint."""

    events: list[UnifiedEvent] = Field(default_factory=list)
    total: int = Field(..., description="Total events matching filters")
    has_more: bool = Field(..., description="More events available")
    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Items per page")

    # Metadata
    chat_count: int = Field(0, description="Number of chat events in response")
    audio_count: int = Field(0, description="Number of audio events in response")
    time_range: dict = Field(default_factory=dict, description="Applied time range")


class TimelineStatsResponse(BaseModel):
    """Statistics for the unified timeline."""

    total_events: int = Field(0)
    chat_messages: int = Field(0)
    audio_transcriptions: int = Field(0)
    oldest_timestamp: int | None = Field(None)
    newest_timestamp: int | None = Field(None)
    unique_sessions: int = Field(0)


# ============================================================================
# Helper Functions
# ============================================================================


def _parse_timestamp(ts: str | int | float) -> int:
    """Convert various timestamp formats to Unix seconds."""
    if isinstance(ts, (int, float)):
        # If it's already a number, check if it's milliseconds or seconds
        if ts > 1e12:  # Likely milliseconds
            return int(ts / 1000)
        return int(ts)

    # ISO string
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except (ValueError, AttributeError):
        return 0


def _get_chat_events(
    doctor_id: str,
    start_ts: int | None,
    end_ts: int | None,
    limit: int,
    offset: int,
) -> tuple[list[UnifiedEvent], int]:
    """Fetch chat events from conversation memory."""
    events: list[UnifiedEvent] = []

    try:
        memory = get_memory_manager(doctor_id)
        result = memory.get_paginated_history(
            offset=offset,
            limit=limit * 2,  # Fetch more to account for time filtering
            session_id=None,
        )

        for idx, interaction in enumerate(result["interactions"]):
            ts = interaction.timestamp

            # Apply time range filter
            if start_ts and ts < start_ts:
                continue
            if end_ts and ts > end_ts:
                continue

            event_type: Literal["chat_user", "chat_assistant"] = (
                "chat_user" if interaction.role == "user" else "chat_assistant"
            )

            events.append(
                UnifiedEvent(
                    id=f"chat-{ts}-{idx}",
                    timestamp=ts,
                    event_type=event_type,
                    content=interaction.content,
                    source="chat",
                    session_id=interaction.session_id,
                    persona=interaction.persona,
                )
            )

        return events[:limit], result["total"]

    except FileNotFoundError:
        return [], 0
    except Exception as e:
        logger.warning("CHAT_EVENTS_FETCH_ERROR", doctor_id=doctor_id, error=str(e))
        return [], 0


def _get_audio_events(
    start_ts: int | None,
    end_ts: int | None,
    limit: int,
    offset: int,
) -> tuple[list[UnifiedEvent], int]:
    """Fetch audio transcription events from HDF5."""
    events: list[UnifiedEvent] = []
    total_count = 0

    try:
        with h5py.File(CORPUS_PATH, "r") as f:
            if "sessions" not in f:
                return [], 0

            sessions_group = f["sessions"]

            # Collect all chunks with timestamps
            all_chunks: list[tuple[int, str, dict]] = []  # (timestamp, session_id, chunk_data)

            for session_id in sessions_group.keys():
                try:
                    session = sessions_group[session_id]
                    if "tasks" not in session:  # type: ignore[operator]
                        continue

                    tasks = session["tasks"]
                    if "TRANSCRIPTION" not in tasks:  # type: ignore[operator]
                        continue

                    trans_task = tasks["TRANSCRIPTION"]
                    if "chunks" not in trans_task:  # type: ignore[operator]
                        continue

                    chunks_group = trans_task["chunks"]

                    for chunk_name in chunks_group.keys():
                        chunk = chunks_group[chunk_name]

                        # Get timestamp
                        created_at = None
                        if "created_at" in chunk:  # type: ignore[operator]
                            created_at_ds = chunk["created_at"]
                            if isinstance(created_at_ds, h5py.Dataset):
                                created_at = created_at_ds[()].decode("utf-8")

                        if not created_at:
                            continue

                        ts = _parse_timestamp(created_at)

                        # Apply time range filter early
                        if start_ts and ts < start_ts:
                            continue
                        if end_ts and ts > end_ts:
                            continue

                        # Read chunk data
                        chunk_data = {
                            "session_id": session_id,
                            "chunk_name": chunk_name,
                        }

                        # Transcript
                        if "transcript" in chunk:  # type: ignore[operator]
                            ds = chunk["transcript"]
                            if isinstance(ds, h5py.Dataset):
                                chunk_data["transcript"] = ds[()].decode("utf-8")

                        # Duration
                        if "duration" in chunk:  # type: ignore[operator]
                            ds = chunk["duration"]
                            if isinstance(ds, h5py.Dataset):
                                chunk_data["duration"] = float(ds[()])

                        # Confidence
                        if "confidence_score" in chunk:  # type: ignore[operator]
                            ds = chunk["confidence_score"]
                            if isinstance(ds, h5py.Dataset):
                                chunk_data["confidence"] = float(ds[()])

                        # Language
                        if "language" in chunk:  # type: ignore[operator]
                            ds = chunk["language"]
                            if isinstance(ds, h5py.Dataset):
                                chunk_data["language"] = ds[()].decode("utf-8")

                        # STT Provider
                        if "stt_provider" in chunk:  # type: ignore[operator]
                            ds = chunk["stt_provider"]
                            if isinstance(ds, h5py.Dataset):
                                chunk_data["stt_provider"] = ds[()].decode("utf-8")

                        # Chunk number (extract from name like "chunk_0")
                        try:
                            chunk_data["chunk_number"] = int(chunk_name.split("_")[1])
                        except (IndexError, ValueError):
                            chunk_data["chunk_number"] = 0

                        all_chunks.append((ts, session_id, chunk_data))

                except Exception as e:
                    logger.warning(
                        "AUDIO_SESSION_READ_ERROR",
                        session_id=session_id,
                        error=str(e),
                    )
                    continue

            # Sort by timestamp (newest first)
            all_chunks.sort(key=lambda x: x[0], reverse=True)
            total_count = len(all_chunks)

            # Apply pagination
            paginated = all_chunks[offset : offset + limit]

            # Convert to UnifiedEvent
            for ts, session_id, chunk_data in paginated:
                events.append(
                    UnifiedEvent(
                        id=f"audio-{session_id}-{chunk_data.get('chunk_number', 0)}",
                        timestamp=ts,
                        event_type="transcription",
                        content=chunk_data.get("transcript", ""),
                        source="audio",
                        session_id=session_id,
                        chunk_number=chunk_data.get("chunk_number"),
                        duration=chunk_data.get("duration"),
                        confidence=chunk_data.get("confidence"),
                        language=chunk_data.get("language"),
                        stt_provider=chunk_data.get("stt_provider"),
                    )
                )

        return events, total_count

    except Exception as e:
        logger.error("AUDIO_EVENTS_FETCH_ERROR", error=str(e), exc_info=True)
        return [], 0


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/timeline/unified",
    response_model=UnifiedTimelineResponse,
    status_code=status.HTTP_200_OK,
)
async def get_unified_timeline(
    doctor_id: str = Query(..., description="Doctor ID (Auth0 user.sub)"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    limit: int = Query(
        TimelineConfig.DEFAULT_LIMIT,
        ge=1,
        le=TimelineConfig.MAX_LIMIT,
        description="Events per page",
    ),
    event_type: EventType = Query(EventType.ALL, description="Filter by event type"),
    start_time: str | None = Query(
        None,
        description="Start time (ISO 8601 or Unix timestamp)",
    ),
    end_time: str | None = Query(
        None,
        description="End time (ISO 8601 or Unix timestamp)",
    ),
) -> UnifiedTimelineResponse:
    """Get unified timeline combining chat messages and audio transcriptions.

    All events are sorted chronologically (newest first) and can be filtered
    by type and time range.

    Philosophy: "No existen sesiones. Solo una conversación infinita."

    Args:
        doctor_id: Doctor identifier (Auth0 user.sub)
        offset: Number of events to skip for pagination
        limit: Maximum events to return (max 200)
        event_type: Filter by "all", "chat", or "audio"
        start_time: Optional start of time range
        end_time: Optional end of time range

    Returns:
        UnifiedTimelineResponse with merged, sorted events
    """
    logger.info(
        "UNIFIED_TIMELINE_REQUEST",
        doctor_id=doctor_id,
        offset=offset,
        limit=limit,
        event_type=event_type.value,
        start_time=start_time,
        end_time=end_time,
    )

    # Parse time range
    start_ts: int | None = None
    end_ts: int | None = None

    if start_time:
        start_ts = _parse_timestamp(start_time)
    if end_time:
        end_ts = _parse_timestamp(end_time)

    # Fetch events based on filter
    chat_events: list[UnifiedEvent] = []
    audio_events: list[UnifiedEvent] = []
    chat_total = 0
    audio_total = 0

    if event_type in (EventType.ALL, EventType.CHAT):
        chat_events, chat_total = _get_chat_events(
            doctor_id=doctor_id,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=limit,
            offset=0 if event_type == EventType.ALL else offset,
        )

    if event_type in (EventType.ALL, EventType.AUDIO):
        audio_events, audio_total = _get_audio_events(
            start_ts=start_ts,
            end_ts=end_ts,
            limit=limit,
            offset=0 if event_type == EventType.ALL else offset,
        )

    # Merge and sort
    all_events = chat_events + audio_events
    all_events.sort(key=lambda e: e.timestamp, reverse=True)

    # Apply pagination to merged result
    if event_type == EventType.ALL:
        all_events = all_events[offset : offset + limit]

    total = chat_total + audio_total if event_type == EventType.ALL else (
        chat_total if event_type == EventType.CHAT else audio_total
    )

    logger.info(
        "UNIFIED_TIMELINE_SUCCESS",
        doctor_id=doctor_id,
        returned=len(all_events),
        chat_count=len([e for e in all_events if e.source == "chat"]),
        audio_count=len([e for e in all_events if e.source == "audio"]),
        total=total,
    )

    return UnifiedTimelineResponse(
        events=all_events,
        total=total,
        has_more=(offset + len(all_events)) < total,
        offset=offset,
        limit=limit,
        chat_count=len([e for e in all_events if e.source == "chat"]),
        audio_count=len([e for e in all_events if e.source == "audio"]),
        time_range={
            "start": start_time,
            "end": end_time,
            "start_ts": start_ts,
            "end_ts": end_ts,
        },
    )


@router.get(
    "/timeline/unified/stats",
    response_model=TimelineStatsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_timeline_stats(
    doctor_id: str = Query(..., description="Doctor ID (Auth0 user.sub)"),
) -> TimelineStatsResponse:
    """Get statistics for the unified timeline.

    Provides counts and metadata without fetching full events.
    Useful for UI indicators and pagination info.
    """
    logger.info("TIMELINE_STATS_REQUEST", doctor_id=doctor_id)

    chat_count = 0
    audio_count = 0
    oldest_ts: int | None = None
    newest_ts: int | None = None
    unique_sessions: set[str] = set()

    # Chat stats
    try:
        memory = get_memory_manager(doctor_id)
        stats = memory.get_stats()
        chat_count = stats.get("total_interactions", 0)
    except Exception:
        pass

    # Audio stats (quick scan)
    try:
        with h5py.File(CORPUS_PATH, "r") as f:
            if "sessions" in f:
                sessions_group = f["sessions"]
                for session_id in sessions_group.keys():
                    unique_sessions.add(session_id)
                    try:
                        session = sessions_group[session_id]
                        if "tasks" in session:  # type: ignore[operator]
                            tasks = session["tasks"]
                            if "TRANSCRIPTION" in tasks:  # type: ignore[operator]
                                trans = tasks["TRANSCRIPTION"]
                                if "chunks" in trans:  # type: ignore[operator]
                                    audio_count += len(trans["chunks"].keys())
                    except Exception:
                        continue
    except Exception:
        pass

    return TimelineStatsResponse(
        total_events=chat_count + audio_count,
        chat_messages=chat_count,
        audio_transcriptions=audio_count,
        oldest_timestamp=oldest_ts,
        newest_timestamp=newest_ts,
        unique_sessions=len(unique_sessions),
    )
