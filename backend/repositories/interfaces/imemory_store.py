"""IMemoryStore - Interface for longitudinal memory storage (audio transcriptions).

Abstracts audio transcription storage (HDF5, PostgreSQL, etc.) from business logic.
Chat messages are handled separately via ConversationMemory (already abstracted).

Clean Architecture:
- DIMemoryService (business logic) → IMemoryStore (interface) → HDF5MemoryStore (implementation)

Benefits:
- Tests can use in-memory mock store
- Easy to swap HDF5 → PostgreSQL
- Separation of concerns (service logic vs storage)

Author: Claude Sonnet 4.5
Created: 2026-01-31 (Replaced patient memory interface with audio-focused one)
Card: DI Refactor Phase 2.4 - Memory Service DI
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypedDict, NotRequired


# ============================================================================
# Data Transfer Objects
# ============================================================================


class AudioEventDict(TypedDict):
    """Audio transcription event data (from HDF5 chunk).

    REQUIRED fields (total=True by default):
    - session_id: Session identifier
    - chunk_number: Chunk index within session
    - transcript: Transcribed text
    - timestamp: Unix timestamp in seconds
    - created_at: ISO 8601 timestamp string

    OPTIONAL fields (NotRequired):
    - duration: Audio duration in seconds
    - confidence: Transcription confidence score 0-1
    - language: Detected language code
    - stt_provider: Speech-to-text provider name

    Type Safety:
    - Accessing required fields: event['session_id'] ✅ (no KeyError possible)
    - Accessing optional fields: event.get('duration') ✅ (returns None if missing)
    """

    # REQUIRED fields (type checker enforces these MUST exist)
    session_id: str
    chunk_number: int
    transcript: str
    timestamp: int  # Unix timestamp (seconds)
    created_at: str  # ISO string

    # OPTIONAL fields (explicitly marked, can be missing)
    duration: NotRequired[float]
    confidence: NotRequired[float]
    language: NotRequired[str]
    stt_provider: NotRequired[str]


class AudioStatsDict(TypedDict):
    """Audio transcription statistics.

    Fields:
    - count: Total number of audio chunks
    - oldest_timestamp: Unix timestamp of oldest chunk (None if no chunks)
    - newest_timestamp: Unix timestamp of newest chunk (None if no chunks)
    - unique_sessions: Number of unique sessions with audio
    """

    count: int
    oldest_timestamp: int | None
    newest_timestamp: int | None
    unique_sessions: int


# ============================================================================
# IMemoryStore Interface
# ============================================================================


class IMemoryStore(ABC):
    """Interface for longitudinal memory storage (audio transcriptions).

    Responsibilities:
    - Store and retrieve audio transcription chunks
    - Filter by doctor_id (multi-tenancy security)
    - Search transcriptions by text query
    - Provide statistics

    Security:
    - ALL methods MUST filter by doctor_id (prevent cross-doctor access)
    - Sessions without owner metadata MUST be excluded (legacy data protection)

    Note:
    - Chat messages are handled separately (via ConversationMemory)
    - This interface focuses on audio transcriptions only

    Clean Architecture Benefits:
    - DIMemoryService doesn't know about HDF5/PostgreSQL
    - Easy to test with in-memory mock
    - Can swap storage backend without changing service
    """

    @abstractmethod
    def get_audio_events(
        self,
        doctor_id: str,
        start_ts: int | None = None,
        end_ts: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AudioEventDict], int]:
        """Fetch audio transcription events for a doctor.

        Args:
            doctor_id: Doctor identifier (JWT user.sub)
            start_ts: Optional start of time range (Unix seconds)
            end_ts: Optional end of time range (Unix seconds)
            limit: Maximum events to return
            offset: Number of events to skip (pagination)

        Returns:
            Tuple of (events, total_count):
            - events: List of audio event dicts (sorted newest first)
            - total_count: Total matching events (for pagination)

        Security:
            MUST filter by doctor_id. Sessions without owner metadata MUST be excluded.

        Example:
            events, total = store.get_audio_events(
                doctor_id="user-123",
                start_ts=1640000000,
                end_ts=1650000000,
                limit=10,
                offset=0,
            )
        """
        pass

    @abstractmethod
    def search_audio_events(
        self,
        doctor_id: str,
        query: str,
        limit: int = 1000,
    ) -> list[AudioEventDict]:
        """Search audio transcriptions by text query.

        Args:
            doctor_id: Doctor identifier
            query: Search query (case-insensitive substring match)
            limit: Maximum results to return (default: 1000 for broad search)

        Returns:
            List of matching audio events (unsorted, unpaginated)
            Caller is responsible for sorting and pagination.

        Security:
            MUST filter by doctor_id. Sessions without owner metadata MUST be excluded.

        Note:
            Uses case-insensitive substring matching (not full-text search).
            For production, consider using vector search or Elasticsearch.

        Example:
            events = store.search_audio_events(
                doctor_id="user-123",
                query="diabetes",
                limit=100,
            )
        """
        pass

    @abstractmethod
    def get_audio_stats(
        self,
        doctor_id: str,
    ) -> AudioStatsDict:
        """Get statistics for audio transcriptions.

        Args:
            doctor_id: Doctor identifier

        Returns:
            Dict with keys:
            - count: Total audio chunks
            - oldest_timestamp: Unix seconds of oldest chunk (or None)
            - newest_timestamp: Unix seconds of newest chunk (or None)
            - unique_sessions: Number of unique sessions

        Security:
            MUST filter by doctor_id. Sessions without owner metadata MUST be excluded.

        Example:
            stats = store.get_audio_stats("user-123")
            # {"count": 150, "oldest_timestamp": 1640000000, ...}
        """
        pass


__all__ = ["IMemoryStore", "AudioEventDict", "AudioStatsDict"]
