"""Domain Events - Base event model and event types.

All domain events inherit from DomainEvent and are immutable, append-only records
of something that happened in the system.

IMPORTANT: Events must NEVER contain PHI (Protected Health Information).
Only include IDs, timestamps, counts, and non-sensitive metadata.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from backend.src.fi_events.domain.metadata import EventMetadata
from pydantic import BaseModel, ConfigDict, Field

# Schema version for all events (bump when breaking changes)
SCHEMA_VERSION = "1.0"


def _generate_ulid() -> str:
    """Generate ULID for event_id (lazy import to avoid circular deps)."""
    try:
        import ulid

        return str(ulid.new())
    except ImportError:
        # Fallback to UUID if ULID not installed
        from uuid import uuid4

        return str(uuid4())


class EventType(str, Enum):
    """Domain event types.

    Naming convention: {AGGREGATE}_{ACTION}
    Examples: TRANSCRIPTION_STARTED, SOAP_GENERATED, SESSION_ENDED
    """

    # Transcription events
    TRANSCRIPTION_STARTED = "TRANSCRIPTION_STARTED"
    TRANSCRIPTION_CHUNK_RECEIVED = "TRANSCRIPTION_CHUNK_RECEIVED"
    TRANSCRIPTION_CHUNK_PROCESSED = "TRANSCRIPTION_CHUNK_PROCESSED"
    TRANSCRIPTION_ENDED = "TRANSCRIPTION_ENDED"
    TRANSCRIPTION_FAILED = "TRANSCRIPTION_FAILED"

    # Session lifecycle
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_UPDATED = "SESSION_UPDATED"
    SESSION_FINALIZED = "SESSION_FINALIZED"

    # SOAP generation
    SOAP_GENERATION_STARTED = "SOAP_GENERATION_STARTED"
    SOAP_GENERATION_COMPLETED = "SOAP_GENERATION_COMPLETED"
    SOAP_GENERATION_FAILED = "SOAP_GENERATION_FAILED"

    # Diarization
    DIARIZATION_STARTED = "DIARIZATION_STARTED"
    DIARIZATION_COMPLETED = "DIARIZATION_COMPLETED"
    DIARIZATION_FAILED = "DIARIZATION_FAILED"

    # Assistant/Chat
    ASSISTANT_MESSAGE_RECEIVED = "ASSISTANT_MESSAGE_RECEIVED"
    ASSISTANT_RESPONSE_GENERATED = "ASSISTANT_RESPONSE_GENERATED"

    # System events
    SYSTEM_ERROR = "SYSTEM_ERROR"
    SYSTEM_HEALTH_CHECK = "SYSTEM_HEALTH_CHECK"


class DomainEvent(BaseModel):
    """Base domain event - immutable record of something that happened.

    All events are append-only and contain:
    - Unique event_id for deduplication
    - event_type for routing/filtering
    - aggregate_id to group related events (e.g., session_id)
    - timestamp for ordering
    - payload with event-specific data (NO PHI!)
    - metadata for audit trail

    Example:
        event = DomainEvent(
            event_type=EventType.TRANSCRIPTION_STARTED,
            aggregate_id="session-123",
            payload={"chunk_count": 0, "mode": "medical"}
        )
    """

    event_id: str = Field(
        default_factory=_generate_ulid, description="Unique event identifier (ULID - time-sortable)"
    )
    event_type: EventType = Field(..., description="Type of domain event")
    aggregate_id: str = Field(
        ..., description="ID of the aggregate this event belongs to (e.g., session_id)"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="When the event occurred (UTC)"
    )
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Event-specific data (MUST NOT contain PHI)"
    )
    metadata: EventMetadata = Field(default_factory=EventMetadata, description="Audit metadata")
    # Versioning
    schema_version: str = Field(
        default=SCHEMA_VERSION, description="Schema version for backward compatibility"
    )
    event_version: int = Field(default=1, description="Event-specific schema version")
    # Idempotency
    dedupe_key: str | None = Field(
        default=None, description="Deduplication key (hash of type+payload)"
    )

    model_config = ConfigDict(frozen=True)

    def with_dedupe_key(self) -> "DomainEvent":
        """Generate dedupe_key if not set.

        Returns:
            New event with dedupe_key set
        """
        if self.dedupe_key is not None:
            return self

        from backend.src.fi_events.domain.identity import generate_dedupe_key

        key = generate_dedupe_key(self.event_type, self.aggregate_id, self.payload)

        # Create new event with dedupe_key (immutable pattern)
        return self.model_copy(update={"dedupe_key": key})


# ============================================================================
# SPECIFIC EVENT TYPES (for type safety and validation)
# ============================================================================


class TranscriptionStartedEvent(DomainEvent):
    """Event emitted when transcription session starts."""

    event_type: EventType = EventType.TRANSCRIPTION_STARTED

    @classmethod
    def create(
        cls,
        session_id: str,
        mode: str = "medical",
        source: str = "stream",
    ) -> "TranscriptionStartedEvent":
        """Factory method to create event with validated payload."""
        return cls(
            aggregate_id=session_id,
            payload={
                "mode": mode,
                "source": source,
            },
        )


class TranscriptionChunkEvent(DomainEvent):
    """Event emitted when a chunk is received/processed."""

    event_type: EventType = EventType.TRANSCRIPTION_CHUNK_RECEIVED

    @classmethod
    def create(
        cls,
        session_id: str,
        chunk_number: int,
        duration_ms: float = 0.0,
        audio_size_bytes: int = 0,
    ) -> "TranscriptionChunkEvent":
        """Factory method - NO transcript text (PHI)."""
        return cls(
            aggregate_id=session_id,
            payload={
                "chunk_number": chunk_number,
                "duration_ms": duration_ms,
                "audio_size_bytes": audio_size_bytes,
            },
        )


class TranscriptionEndedEvent(DomainEvent):
    """Event emitted when transcription session ends."""

    event_type: EventType = EventType.TRANSCRIPTION_ENDED

    @classmethod
    def create(
        cls,
        session_id: str,
        total_chunks: int,
        total_duration_ms: float,
        status: str = "completed",
    ) -> "TranscriptionEndedEvent":
        """Factory method with summary stats (no PHI)."""
        return cls(
            aggregate_id=session_id,
            payload={
                "total_chunks": total_chunks,
                "total_duration_ms": total_duration_ms,
                "status": status,
            },
        )


class TranscriptionFailedEvent(DomainEvent):
    """Event emitted when transcription fails."""

    event_type: EventType = EventType.TRANSCRIPTION_FAILED

    @classmethod
    def create(
        cls,
        session_id: str,
        error_code: str,
        error_message: str,  # Sanitized, no stack traces
    ) -> "TranscriptionFailedEvent":
        """Factory method with error info (sanitized)."""
        return cls(
            aggregate_id=session_id,
            payload={
                "error_code": error_code,
                "error_message": error_message[:200],  # Truncate
            },
        )


class SOAPGenerationEvent(DomainEvent):
    """Event for SOAP note generation lifecycle."""

    @classmethod
    def started(cls, session_id: str) -> "SOAPGenerationEvent":
        """SOAP generation started."""
        return cls(
            event_type=EventType.SOAP_GENERATION_STARTED, aggregate_id=session_id, payload={}
        )

    @classmethod
    def completed(
        cls,
        session_id: str,
        quality_score: float,
        completeness: float,
    ) -> "SOAPGenerationEvent":
        """SOAP generation completed (no actual SOAP content - PHI)."""
        return cls(
            event_type=EventType.SOAP_GENERATION_COMPLETED,
            aggregate_id=session_id,
            payload={
                "quality_score": quality_score,
                "completeness": completeness,
            },
        )

    @classmethod
    def failed(cls, session_id: str, error_code: str) -> "SOAPGenerationEvent":
        """SOAP generation failed."""
        return cls(
            event_type=EventType.SOAP_GENERATION_FAILED,
            aggregate_id=session_id,
            payload={"error_code": error_code},
        )
