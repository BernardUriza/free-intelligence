"""Event Metadata - Audit trail information for events.

Metadata captures context about who/what generated the event,
without including any PHI or sensitive data.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class EventMetadata(BaseModel):
    """Audit metadata for domain events.

    Captures:
    - Source system/service that generated the event
    - Correlation ID for tracing across services
    - Schema version for backward compatibility
    - Timezone for display purposes

    Does NOT capture:
    - User IDs (could be PHI in medical context)
    - IP addresses
    - Any patient identifiers
    """

    source: str = Field(default="fi_backend", description="Service/module that generated the event")
    correlation_id: str | None = Field(
        default=None, description="Request correlation ID for distributed tracing"
    )
    schema_version: str = Field(
        default="1.0", description="Event schema version for backward compatibility"
    )
    timezone: str = Field(
        default="America/Mexico_City", description="Timezone for display (data stored in UTC)"
    )
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the event was recorded (may differ from event timestamp)",
    )

    model_config = ConfigDict(frozen=True)
