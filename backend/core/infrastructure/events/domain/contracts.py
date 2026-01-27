"""Event Contracts - Versioned schemas with strict validation.

Contracts define the exact shape of event payloads, enabling:
- Schema versioning (breaking changes require new version)
- Validation at emit time (fail fast)
- Upcasting old events to new schema
- Type safety across the system

Each contract has:
- event_type: The EventType it validates
- version: Schema version (semver-ish: 1, 2, 3...)
- schema: Pydantic model with strict validation
- upcaster: Optional function to migrate from previous version

Usage:
    from backend.core.infrastructure.events.domain.contracts import validate_payload, get_contract

    # Validate before emitting
    validated = validate_payload(EventType.TRANSCRIPTION_STARTED, payload)

    # Get contract for introspection
    contract = get_contract(EventType.TRANSCRIPTION_STARTED)
    print(contract.version, contract.schema.model_json_schema())
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from backend.utils.common.logging.logger import get_logger
from backend.core.infrastructure.events.domain.events import EventType
from pydantic import BaseModel, Field, field_validator

logger = get_logger(__name__)

# Current schema version for all contracts
SCHEMA_VERSION = "1.0"

T = TypeVar("T", bound=BaseModel)


# ============================================================================
# PAYLOAD SCHEMAS (Strict Pydantic models)
# ============================================================================


class TranscriptionStartedPayload(BaseModel):
    """Payload for TRANSCRIPTION_STARTED event."""

    mode: str = Field(..., pattern="^(medical|chat)$")
    source: str = Field(default="stream")

    class Config:
        extra = "forbid"  # No extra fields allowed


class TranscriptionChunkPayload(BaseModel):
    """Payload for TRANSCRIPTION_CHUNK_RECEIVED event."""

    chunk_number: int = Field(..., ge=0, le=10000)
    duration_ms: float = Field(default=0.0, ge=0)
    audio_size_bytes: int = Field(default=0, ge=0)

    class Config:
        extra = "forbid"

    @field_validator("chunk_number")
    @classmethod
    def validate_chunk_number(cls, v: int) -> int:
        if v < 0:
            raise ValueError("chunk_number must be >= 0")
        return v


class TranscriptionEndedPayload(BaseModel):
    """Payload for TRANSCRIPTION_ENDED event."""

    total_chunks: int = Field(..., ge=0)
    total_duration_ms: float = Field(..., ge=0)
    status: str = Field(default="completed", pattern="^(completed|cancelled|timeout)$")

    class Config:
        extra = "forbid"


class TranscriptionFailedPayload(BaseModel):
    """Payload for TRANSCRIPTION_FAILED event."""

    error_code: str = Field(..., min_length=1, max_length=50)
    error_message: str = Field(..., max_length=200)  # Truncated, no stack traces

    class Config:
        extra = "forbid"


class SessionCreatedPayload(BaseModel):
    """Payload for SESSION_CREATED event."""

    session_type: str = Field(default="medical")
    created_by: str = Field(default="system")  # NOT user_id (PHI)

    class Config:
        extra = "forbid"


class SessionFinalizedPayload(BaseModel):
    """Payload for SESSION_FINALIZED event."""

    total_duration_ms: float = Field(..., ge=0)
    total_chunks: int = Field(..., ge=0)
    has_soap: bool = Field(default=False)
    has_diarization: bool = Field(default=False)

    class Config:
        extra = "forbid"


class SOAPGenerationStartedPayload(BaseModel):
    """Payload for SOAP_GENERATION_STARTED event."""

    trigger: str = Field(default="manual", pattern="^(manual|auto|scheduled)$")

    class Config:
        extra = "forbid"


class SOAPGenerationCompletedPayload(BaseModel):
    """Payload for SOAP_GENERATION_COMPLETED event."""

    quality_score: float = Field(..., ge=0, le=1)
    completeness: float = Field(..., ge=0, le=100)
    sections_generated: list[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class SOAPGenerationFailedPayload(BaseModel):
    """Payload for SOAP_GENERATION_FAILED event."""

    error_code: str = Field(..., min_length=1, max_length=50)

    class Config:
        extra = "forbid"


class DiarizationCompletedPayload(BaseModel):
    """Payload for DIARIZATION_COMPLETED event."""

    speaker_count: int = Field(..., ge=1, le=20)
    total_segments: int = Field(..., ge=0)

    class Config:
        extra = "forbid"


class AssistantMessagePayload(BaseModel):
    """Payload for ASSISTANT_MESSAGE_RECEIVED event."""

    message_type: str = Field(..., pattern="^(user|assistant|system)$")
    token_count: int = Field(default=0, ge=0)
    persona: str = Field(default="default")
    # NO message content - that's PHI

    class Config:
        extra = "forbid"


class AssistantResponsePayload(BaseModel):
    """Payload for ASSISTANT_RESPONSE_GENERATED event."""

    message_type: str = Field(default="assistant", pattern="^(assistant)$")
    token_count: int = Field(default=0, ge=0)
    total_chunks: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    provider: str = Field(default="unknown")
    # NO response content - that's PHI

    class Config:
        extra = "forbid"


class SystemErrorPayload(BaseModel):
    """Payload for SYSTEM_ERROR event."""

    error_code: str = Field(..., min_length=1, max_length=50)
    component: str = Field(..., min_length=1, max_length=100)
    # NO stack trace or sensitive details

    class Config:
        extra = "forbid"


# ============================================================================
# CONTRACT REGISTRY
# ============================================================================


class EventContract:
    """Contract for an event type with versioning."""

    def __init__(
        self,
        event_type: EventType,
        version: int,
        schema: type[BaseModel],
        upcaster: Callable[[dict, int], dict] | None = None,
    ):
        self.event_type = event_type
        self.version = version
        self.schema = schema
        self.upcaster = upcaster

    def validate(self, payload: dict[str, Any]) -> BaseModel:
        """Validate payload against schema.

        Args:
            payload: Raw payload dict

        Returns:
            Validated Pydantic model

        Raises:
            ValueError: If validation fails
        """
        try:
            return self.schema.model_validate(payload)
        except Exception as e:
            raise ValueError(f"Payload validation failed for {self.event_type.value}: {e}") from e

    def upcast(self, payload: dict[str, Any], from_version: int) -> dict[str, Any]:
        """Upcast payload from older version.

        Args:
            payload: Old payload
            from_version: Version of the old payload

        Returns:
            Upcasted payload compatible with current version
        """
        if self.upcaster is None:
            return payload
        return self.upcaster(payload, from_version)


# Contract registry: EventType -> EventContract
_CONTRACTS: dict[EventType, EventContract] = {}


def register_contract(
    event_type: EventType,
    version: int,
    schema: type[BaseModel],
    upcaster: Callable[[dict, int], dict] | None = None,
) -> None:
    """Register a contract for an event type."""
    _CONTRACTS[event_type] = EventContract(event_type, version, schema, upcaster)


def get_contract(event_type: EventType) -> EventContract | None:
    """Get contract for event type."""
    return _CONTRACTS.get(event_type)


def validate_payload(event_type: EventType, payload: dict[str, Any]) -> dict[str, Any]:
    """Validate payload against contract.

    Args:
        event_type: Type of event
        payload: Raw payload dict

    Returns:
        Validated payload as dict

    Raises:
        ValueError: If validation fails or no contract exists
    """
    contract = get_contract(event_type)
    if contract is None:
        # No contract = allow any payload (backward compat)
        logger.warning("NO_CONTRACT_FOR_EVENT", event_type=event_type.value)
        return payload

    validated = contract.validate(payload)
    return validated.model_dump()


def upcast_payload(
    event_type: EventType,
    payload: dict[str, Any],
    from_version: int,
) -> dict[str, Any]:
    """Upcast payload from older version to current.

    Args:
        event_type: Type of event
        payload: Old payload
        from_version: Version of the old payload

    Returns:
        Upcasted payload
    """
    contract = get_contract(event_type)
    if contract is None:
        return payload

    if from_version >= contract.version:
        return payload  # Already current

    return contract.upcast(payload, from_version)


# ============================================================================
# UPCASTERS (Migrate old events to new schema)
# ============================================================================


def _upcast_transcription_started_v0_to_v1(payload: dict, from_version: int) -> dict:
    """Upcast TRANSCRIPTION_STARTED from v0 (no version) to v1."""
    # v0 might have "workflow_mode" instead of "mode"
    if "workflow_mode" in payload and "mode" not in payload:
        payload["mode"] = payload.pop("workflow_mode")

    # Ensure required fields
    payload.setdefault("mode", "medical")
    payload.setdefault("source", "stream")

    return payload


def _upcast_transcription_chunk_v0_to_v1(payload: dict, from_version: int) -> dict:
    """Upcast TRANSCRIPTION_CHUNK from v0 to v1."""
    # v0 might have "size" instead of "audio_size_bytes"
    if "size" in payload and "audio_size_bytes" not in payload:
        payload["audio_size_bytes"] = payload.pop("size")

    # Ensure required fields
    payload.setdefault("duration_ms", 0.0)
    payload.setdefault("audio_size_bytes", 0)

    return payload


# ============================================================================
# REGISTER ALL CONTRACTS
# ============================================================================


def _register_all_contracts() -> None:
    """Register all event contracts."""
    # Transcription events
    register_contract(
        EventType.TRANSCRIPTION_STARTED,
        version=1,
        schema=TranscriptionStartedPayload,
        upcaster=_upcast_transcription_started_v0_to_v1,
    )
    register_contract(
        EventType.TRANSCRIPTION_CHUNK_RECEIVED,
        version=1,
        schema=TranscriptionChunkPayload,
        upcaster=_upcast_transcription_chunk_v0_to_v1,
    )
    register_contract(
        EventType.TRANSCRIPTION_ENDED,
        version=1,
        schema=TranscriptionEndedPayload,
    )
    register_contract(
        EventType.TRANSCRIPTION_FAILED,
        version=1,
        schema=TranscriptionFailedPayload,
    )

    # Session events
    register_contract(
        EventType.SESSION_CREATED,
        version=1,
        schema=SessionCreatedPayload,
    )
    register_contract(
        EventType.SESSION_FINALIZED,
        version=1,
        schema=SessionFinalizedPayload,
    )

    # SOAP events
    register_contract(
        EventType.SOAP_GENERATION_STARTED,
        version=1,
        schema=SOAPGenerationStartedPayload,
    )
    register_contract(
        EventType.SOAP_GENERATION_COMPLETED,
        version=1,
        schema=SOAPGenerationCompletedPayload,
    )
    register_contract(
        EventType.SOAP_GENERATION_FAILED,
        version=1,
        schema=SOAPGenerationFailedPayload,
    )

    # Diarization events
    register_contract(
        EventType.DIARIZATION_COMPLETED,
        version=1,
        schema=DiarizationCompletedPayload,
    )

    # Assistant events
    register_contract(
        EventType.ASSISTANT_MESSAGE_RECEIVED,
        version=1,
        schema=AssistantMessagePayload,
    )
    register_contract(
        EventType.ASSISTANT_RESPONSE_GENERATED,
        version=1,
        schema=AssistantResponsePayload,
    )

    # System events
    register_contract(
        EventType.SYSTEM_ERROR,
        version=1,
        schema=SystemErrorPayload,
    )

    logger.info("EVENT_CONTRACTS_REGISTERED", count=len(_CONTRACTS))


# Auto-register on module load
_register_all_contracts()


# ============================================================================
# HELPERS
# ============================================================================


def list_contracts() -> list[dict]:
    """List all registered contracts.

    Returns:
        List of contract info dicts
    """
    return [
        {
            "event_type": c.event_type.value,
            "version": c.version,
            "schema": c.schema.__name__,
            "has_upcaster": c.upcaster is not None,
        }
        for c in _CONTRACTS.values()
    ]


def get_schema_json(event_type: EventType) -> dict | None:
    """Get JSON schema for event type.

    Args:
        event_type: The event type

    Returns:
        JSON schema dict or None
    """
    contract = get_contract(event_type)
    if contract is None:
        return None
    return contract.schema.model_json_schema()
