#!/usr/bin/env python3
"""
Free Intelligence - Timeline Models

Modelo de datos para Timeline AURITY con causalidad (quién→qué→cuándo→por qué).
Sin spoilers de audio crudo - política de redacción aplicada.

Card: [P0][Área: UX/UI][Tipo: feature] Memoria legible — Timeline AURITY
Sprint: SPR-2025W44
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import hashlib
import uuid


# ============================================================================
# ENUMS
# ============================================================================

class TimelineEventType(str, Enum):
    """Tipos de eventos en timeline."""
    # User actions
    USER_MESSAGE = "user_message"
    USER_UPLOAD = "user_upload"
    USER_EDIT = "user_edit"

    # System actions
    ASSISTANT_RESPONSE = "assistant_response"
    EXTRACTION_STARTED = "extraction_started"
    EXTRACTION_COMPLETED = "extraction_completed"

    # Medical actions
    SOAP_SECTION_UPDATED = "soap_section_updated"
    SOAP_COMPLETED = "soap_completed"
    DIAGNOSIS_SUGGESTED = "diagnosis_suggested"

    # Critical events
    CRITICAL_PATTERN_DETECTED = "critical_pattern_detected"
    URGENCY_ESCALATED = "urgency_escalated"

    # Policy events
    REDACTION_APPLIED = "redaction_applied"
    EXPORT_CREATED = "export_created"


class CausalityType(str, Enum):
    """Tipo de relación causal entre eventos."""
    CAUSED_BY = "caused_by"           # Este evento fue causado por...
    TRIGGERED = "triggered"           # Este evento disparó...
    UPDATED = "updated"               # Este evento actualizó...
    REPLACED = "replaced"             # Este evento reemplazó...
    CONFIRMED = "confirmed"           # Este evento confirmó...
    CONTRADICTED = "contradicted"     # Este evento contradijo...


class RedactionPolicy(str, Enum):
    """Política de redacción de contenido."""
    NONE = "none"                     # Sin redacción (datos públicos)
    SUMMARY = "summary"               # Solo resumen (no texto crudo)
    METADATA = "metadata"             # Solo metadata (sin contenido)
    FULL = "full"                     # Redacción completa (solo hash)


class TimelineMode(str, Enum):
    """Modo de generación de timeline."""
    AUTO = "auto"                     # Automático con Ollama
    MANUAL = "manual"                 # Manual puro
    ASSISTED = "assisted"             # Manual con sugerencias automáticas


# ============================================================================
# MODELS
# ============================================================================

class TimelineEventCausality(BaseModel):
    """
    Relación causal entre eventos.

    Representa quién→qué→cuándo→por qué.
    """
    related_event_id: str = Field(..., description="UUID del evento relacionado")
    causality_type: CausalityType = Field(..., description="Tipo de relación causal")
    explanation: Optional[str] = Field(None, description="Explicación de la causalidad")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confianza en la relación (0-1)")

class TimelineEvent(BaseModel):
    """
    Evento individual en timeline con causalidad y redacción.

    Campos obligatorios:
    - event_id: UUID único
    - event_type: Tipo de evento (user_message, extraction_completed, etc.)
    - timestamp: Cuándo ocurrió (ISO 8601 con timezone)
    - who: Quién ejecutó (user_hash, assistant, system)
    - what: Qué sucedió (descripción redactada)
    - why: Por qué sucedió (causalidad)

    Política de redacción:
    - raw_content: NUNCA se expone en timeline
    - summary: Resumen automático o manual (según redaction_policy)
    - content_hash: SHA256 para trazabilidad sin spoilers
    """

    # Core fields (obligatorios)
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: TimelineEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Causalidad (quién→qué→cuándo→por qué)
    who: str = Field(..., description="Quién ejecutó (user_hash/assistant/system)")
    what: str = Field(..., description="Qué sucedió (descripción redactada)")
    causality: List[TimelineEventCausality] = Field(
        default_factory=list,
        description="Por qué sucedió (relaciones causales)"
    )

    # Contenido (con redacción)
    summary: Optional[str] = Field(None, description="Resumen del evento (redactado)")
    content_hash: str = Field(..., description="SHA256 del contenido crudo (sin exponer)")
    redaction_policy: RedactionPolicy = Field(
        default=RedactionPolicy.SUMMARY,
        description="Política de redacción aplicada"
    )

    # Metadata
    session_id: Optional[str] = Field(None, description="ID de sesión/consulta")
    reference_id: Optional[str] = Field(None, description="ID en event store (HDF5)")
    tags: List[str] = Field(default_factory=list, description="Tags para filtrado")

    # Auto-timeline metadata
    auto_generated: bool = Field(False, description="Si fue generado automáticamente")
    generation_mode: TimelineMode = Field(
        default=TimelineMode.MANUAL,
        description="Modo de generación (auto/manual/assisted)"
    )
    confidence_score: float = Field(
        1.0, ge=0.0, le=1.0,
        description="Confianza en el evento (auto-timeline)"
    )

    def compute_content_hash(self, raw_content: str) -> str:
        """Compute SHA256 hash of raw content without storing it."""
        return hashlib.sha256(raw_content.encode()).hexdigest()


class Timeline(BaseModel):
    """
    Timeline completo de una consulta o sesión.

    Colección ordenada de eventos con causalidad y redacción.
    """

    timeline_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(..., description="ID de consulta/sesión")
    owner_hash: str = Field(..., description="Hash del propietario (privacidad)")

    # Events (ordenados cronológicamente)
    events: List[TimelineEvent] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Generation metadata
    generation_mode: TimelineMode = Field(
        default=TimelineMode.MANUAL,
        description="Modo de generación predominante"
    )
    auto_events_count: int = Field(0, description="Número de eventos auto-generados")
    manual_events_count: int = Field(0, description="Número de eventos manuales")

    # Redaction stats
    redaction_stats: Dict[str, int] = Field(
        default_factory=lambda: {
            "none": 0,
            "summary": 0,
            "metadata": 0,
            "full": 0
        },
        description="Estadísticas de redacción"
    )

    def add_event(self, event: TimelineEvent):
        """Add event to timeline and update metadata."""
        self.events.append(event)
        self.updated_at = datetime.now(timezone.utc)

        # Update counters
        if event.auto_generated:
            self.auto_events_count += 1
        else:
            self.manual_events_count += 1

        # Update redaction stats
        policy_key = event.redaction_policy.value
        if policy_key in self.redaction_stats:
            self.redaction_stats[policy_key] += 1

    def get_events_by_type(self, event_type: TimelineEventType) -> List[TimelineEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_by_who(self, who: str) -> List[TimelineEvent]:
        """Get all events by a specific actor."""
        return [e for e in self.events if e.who == who]

    def get_causal_chain(self, event_id: str) -> List[TimelineEvent]:
        """
        Get causal chain for an event (all related events).

        Returns list of events in causal order.
        """
        chain = []
        event = self.get_event_by_id(event_id)

        if not event:
            return chain

        chain.append(event)

        # Follow causality backwards
        for causality in event.causality:
            related_event = self.get_event_by_id(causality.related_event_id)
            if related_event and related_event not in chain:
                chain.insert(0, related_event)

        return chain

    def get_event_by_id(self, event_id: str) -> Optional[TimelineEvent]:
        """Get event by ID."""
        for event in self.events:
            if event.event_id == event_id:
                return event
        return None

    def export_to_dict(self) -> Dict[str, Any]:
        """Export timeline to dict (for JSON/HDF5)."""
        return {
            "timeline_id": self.timeline_id,
            "session_id": self.session_id,
            "owner_hash": self.owner_hash,
            "events": [e.model_dump() for e in self.events],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "generation_mode": self.generation_mode.value,
            "auto_events_count": self.auto_events_count,
            "manual_events_count": self.manual_events_count,
            "redaction_stats": self.redaction_stats
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_timeline_event(
    event_type: TimelineEventType,
    who: str,
    what: str,
    raw_content: str,
    summary: Optional[str] = None,
    causality: Optional[List[TimelineEventCausality]] = None,
    redaction_policy: RedactionPolicy = RedactionPolicy.SUMMARY,
    session_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    auto_generated: bool = False,
    generation_mode: TimelineMode = TimelineMode.MANUAL
) -> TimelineEvent:
    """
    Helper function to create timeline event with proper redaction.

    Args:
        event_type: Type of event
        who: Actor (user_hash, assistant, system)
        what: What happened (redacted description)
        raw_content: Original content (will be hashed, not stored)
        summary: Optional summary (if None, use 'what')
        causality: Optional causal relations
        redaction_policy: Redaction policy to apply
        session_id: Optional session ID
        tags: Optional tags
        auto_generated: If auto-generated
        generation_mode: Generation mode

    Returns:
        TimelineEvent instance
    """
    # Compute content hash (without storing raw content)
    content_hash = hashlib.sha256(raw_content.encode()).hexdigest()

    return TimelineEvent(
        event_type=event_type,
        who=who,
        what=what,
        summary=summary or what,
        content_hash=content_hash,
        redaction_policy=redaction_policy,
        causality=causality or [],
        session_id=session_id,
        tags=tags or [],
        auto_generated=auto_generated,
        generation_mode=generation_mode
    )


def create_causality(
    related_event_id: str,
    causality_type: CausalityType,
    explanation: Optional[str] = None,
    confidence: float = 1.0
) -> TimelineEventCausality:
    """Helper function to create causality relation."""
    return TimelineEventCausality(
        related_event_id=related_event_id,
        causality_type=causality_type,
        explanation=explanation,
        confidence=confidence
    )


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    print("📋 FREE INTELLIGENCE - TIMELINE MODELS DEMO")
    print("=" * 60)
    print()

    # Create timeline
    timeline = Timeline(
        session_id="session_demo_001",
        owner_hash="abc123def456"
    )

    # Event 1: User sends message
    event1 = create_timeline_event(
        event_type=TimelineEventType.USER_MESSAGE,
        who="user_abc123",
        what="Usuario reporta dolor de pecho",
        raw_content="Tengo dolor en el pecho desde hace 2 horas",
        summary="Dolor torácico agudo (2h evolución)",
        redaction_policy=RedactionPolicy.SUMMARY,
        session_id="session_demo_001",
        tags=["symptoms", "chest_pain"],
        auto_generated=False
    )
    timeline.add_event(event1)

    # Event 2: Extraction started (caused by event1)
    event2 = create_timeline_event(
        event_type=TimelineEventType.EXTRACTION_STARTED,
        who="system",
        what="Sistema inicia extracción médica",
        raw_content="EXTRACTION_STARTED",
        causality=[
            create_causality(
                related_event_id=event1.event_id,
                causality_type=CausalityType.TRIGGERED,
                explanation="Usuario envió mensaje inicial",
                confidence=1.0
            )
        ],
        redaction_policy=RedactionPolicy.METADATA,
        session_id="session_demo_001",
        tags=["system", "extraction"],
        auto_generated=True,
        generation_mode=TimelineMode.AUTO
    )
    timeline.add_event(event2)

    # Event 3: Critical pattern detected (caused by event2)
    event3 = create_timeline_event(
        event_type=TimelineEventType.CRITICAL_PATTERN_DETECTED,
        who="system",
        what="⚠️ Patrón crítico detectado: posible síndrome coronario agudo",
        raw_content="CRITICAL: Chest pain + risk factors = ACS",
        summary="Dolor torácico con factores de riesgo cardiovascular",
        causality=[
            create_causality(
                related_event_id=event2.event_id,
                causality_type=CausalityType.CAUSED_BY,
                explanation="Extracción identificó patrón de alto riesgo",
                confidence=0.85
            )
        ],
        redaction_policy=RedactionPolicy.SUMMARY,
        session_id="session_demo_001",
        tags=["critical", "acs", "widow_maker"],
        auto_generated=True,
        generation_mode=TimelineMode.AUTO
    )
    timeline.add_event(event3)

    print(f"Timeline created: {timeline.timeline_id}")
    print(f"Session: {timeline.session_id}")
    print(f"Events: {len(timeline.events)}")
    print(f"Auto-generated: {timeline.auto_events_count}")
    print(f"Manual: {timeline.manual_events_count}")
    print()

    print("Events:")
    for i, event in enumerate(timeline.events, 1):
        print(f"\n{i}. [{event.event_type.value}] {event.what}")
        print(f"   Who: {event.who}")
        print(f"   When: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Redaction: {event.redaction_policy.value}")
        print(f"   Hash: {event.content_hash[:16]}...")

        if event.causality:
            print(f"   Causality:")
            for causality in event.causality:
                print(f"      → {causality.causality_type.value}: {causality.explanation}")

    print()
    print("Causal chain for event 3:")
    chain = timeline.get_causal_chain(event3.event_id)
    for event in chain:
        print(f"   → {event.what}")

    print()
    print("Redaction stats:")
    for policy, count in timeline.redaction_stats.items():
        print(f"   {policy}: {count}")
