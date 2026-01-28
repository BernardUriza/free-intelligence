"""Longitudinal Memory API - Memoria Longitudinal (THIN ROUTER).

REFACTORED: All business logic delegated to DIMemoryService.

Single endpoint that combines:
- Chat messages (from conversation memory)
- Audio transcriptions (from sessions HDF5)

All sorted chronologically with pagination and time range filters.

Philosophy: "No existen sesiones. Solo una conversación infinita."

Author: Claude Code
Created: 2025-11-22
Refactored: 2026-01-28 (Phase 2.3 - DI pattern)
Card: Backend Refactor Phase 2.3 - Service Refactoring
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from backend.services.memory.dependencies import get_memory_service
from backend.services.memory.services.di_memory_service import DIMemoryService
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

logger = get_logger(__name__)

router = APIRouter(prefix="/timeline/memory")


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


class MemoryEvent(BaseModel):
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


class LongitudinalMemoryResponse(BaseModel):
    """Response for longitudinal memory endpoint."""

    events: list[MemoryEvent] = Field(default_factory=list)
    total: int = Field(..., description="Total events matching filters")
    has_more: bool = Field(..., description="More events available")
    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Items per page")

    # Metadata
    chat_count: int = Field(0, description="Number of chat events in response")
    audio_count: int = Field(0, description="Number of audio events in response")
    time_range: dict = Field(default_factory=dict, description="Applied time range")


class MemoryStatsResponse(BaseModel):
    """Statistics for the unified timeline."""

    total_events: int = Field(0)
    chat_messages: int = Field(0)
    audio_transcriptions: int = Field(0)
    oldest_timestamp: int | None = Field(None)
    newest_timestamp: int | None = Field(None)
    unique_sessions: int = Field(0)


# ============================================================================
# Note: Helper functions removed - now in DIMemoryService
# - _parse_timestamp() → service method
# - _get_chat_events() → service method
# - _get_audio_events() → service method
# ============================================================================


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "",
    response_model=LongitudinalMemoryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_longitudinal_memory(
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
    service: DIMemoryService = Depends(get_memory_service),
) -> LongitudinalMemoryResponse:
    """Get longitudinal memory combining chat messages and audio transcriptions (THIN ROUTER).

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
        service: Memory service (injected by FastAPI Depends)

    Returns:
        LongitudinalMemoryResponse with merged, sorted events
    """
    # Delegate to service (all business logic)
    result = await service.get_longitudinal_memory(
        doctor_id=doctor_id,
        offset=offset,
        limit=limit,
        event_type=event_type.value,
        start_time=start_time,
        end_time=end_time,
    )

    # Map service result to API response
    return LongitudinalMemoryResponse(**result)


@router.get(
    "/search",
    response_model=LongitudinalMemoryResponse,
    status_code=status.HTTP_200_OK,
)
async def search_memory(
    doctor_id: str = Query(..., description="Doctor ID (Auth0 user.sub)"),
    query: str = Query(..., min_length=1, max_length=500, description="Search query"),
    limit: int = Query(50, ge=1, le=TimelineConfig.MAX_LIMIT),
    offset: int = Query(0, ge=0),
    service: DIMemoryService = Depends(get_memory_service),
) -> LongitudinalMemoryResponse:
    """Search longitudinal memory by text query (THIN ROUTER).

    Uses case-insensitive substring matching across content.
    Searches both chat messages and audio transcriptions.

    Returns results sorted by timestamp (newest first).
    Future enhancement: Semantic search with embeddings.

    Args:
        doctor_id: Doctor identifier (Auth0 user.sub)
        query: Search text (1-500 characters)
        limit: Maximum events to return (max 200)
        offset: Number of events to skip for pagination
        service: Memory service (injected by FastAPI Depends)

    Returns:
        LongitudinalMemoryResponse with search results
    """
    # Delegate to service (all business logic)
    result = await service.search_memory(
        doctor_id=doctor_id,
        query=query,
        limit=limit,
        offset=offset,
    )

    # Map service result to API response
    return LongitudinalMemoryResponse(**result)


@router.get(
    "/stats",
    response_model=MemoryStatsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_memory_stats(
    doctor_id: str = Query(..., description="Doctor ID (Auth0 user.sub)"),
    service: DIMemoryService = Depends(get_memory_service),
) -> MemoryStatsResponse:
    """Get statistics for the longitudinal memory (THIN ROUTER).

    Provides counts and metadata without fetching full events.
    Useful for UI indicators and pagination info.

    Args:
        doctor_id: Doctor identifier (Auth0 user.sub)
        service: Memory service (injected by FastAPI Depends)

    Returns:
        MemoryStatsResponse with aggregate statistics
    """
    # Delegate to service (all business logic)
    result = await service.get_stats(doctor_id=doctor_id)

    # Map service result to API response
    return MemoryStatsResponse(**result)
