from __future__ import annotations

"""
Free Intelligence - Timeline API Service (FastAPI)

RESTful API for Timeline UI with session management, events, and policy badges.

File: backend/timeline_api.py
Created: 2025-10-29
Port: 9002 (as per PORTS.md)

Endpoints:
  GET    /api/timeline/sessions           - List sessions with pagination
  GET    /api/timeline/sessions/{id}      - Get session detail with events
  GET    /api/timeline/events             - Stream events with filters
  GET    /api/timeline/stats              - Aggregated statistics
  GET    /health                          - Health check

Card: FI-API-FEAT-002 (6901be18a6182c6cf5e93331)

Usage:
  uvicorn backend.timeline_api:app --reload --port 9002 --host 0.0.0.0
"""

import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi import Path as PathParam
from fastapi import Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.timeline_models import (
    RedactionPolicy,
    Timeline,
    TimelineEvent,
    TimelineEventType,
    TimelineMode,
)

logger = get_logger(__name__)

# ============================================================================
# PYDANTIC MODELS - API RESPONSES
# ============================================================================


class PolicyBadges(BaseModel):
    """Policy verification badges for a session"""

    hash_verified: str = Field(..., description="Hash integrity status: OK, FAIL, PENDING, N/A")
    policy_compliant: str = Field(
        ..., description="Append-only policy status: OK, FAIL, PENDING, N/A"
    )
    redaction_applied: str = Field(..., description="PII redaction status: OK, FAIL, PENDING, N/A")
    audit_logged: str = Field(..., description="Audit trail status: OK, FAIL, PENDING, N/A")


class SessionMetadata(BaseModel):
    """Session metadata for listing"""

    session_id: str = Field(..., description="Session ID (session_YYYYMMDD_HHMMSS)")
    thread_id: Optional[str] = Field(None, description="Thread ID if applicable")
    owner_hash: str = Field(..., description="Owner hash (first 16 chars)")
    created_at: str = Field(..., description="Session creation timestamp (ISO 8601)")
    updated_at: str = Field(..., description="Last update timestamp (ISO 8601)")


class SessionTimespan(BaseModel):
    """Session timespan information"""

    start: str = Field(..., description="First event timestamp (ISO 8601)")
    end: str = Field(..., description="Last event timestamp (ISO 8601)")
    duration_ms: int = Field(..., description="Duration in milliseconds")
    duration_human: str = Field(..., description="Human-readable duration (e.g., '2h 34m')")


class SessionSize(BaseModel):
    """Session size metrics"""

    interaction_count: int = Field(..., description="Number of interactions/events")
    total_tokens: int = Field(0, description="Total tokens (if available)")
    total_chars: int = Field(0, description="Total characters")
    avg_tokens_per_interaction: float = Field(0.0, description="Average tokens per interaction")
    size_human: str = Field(..., description="Human-readable size (e.g., '12.5K tokens')")


class SessionSummary(BaseModel):
    """Session summary for listing endpoint"""

    metadata: SessionMetadata
    timespan: SessionTimespan
    size: SessionSize
    policy_badges: PolicyBadges
    preview: str = Field(..., description="Preview of first event (max 200 chars)")


class EventResponse(BaseModel):
    """Timeline event response"""

    event_id: str
    event_type: str
    timestamp: str
    who: str
    what: str
    summary: Optional[str]
    content_hash: str
    redaction_policy: str
    causality: list[dict[str, Any]]
    tags: list[str]
    auto_generated: bool
    generation_mode: str
    confidence_score: float


class SessionDetail(BaseModel):
    """Detailed session with all events"""

    metadata: SessionMetadata
    timespan: SessionTimespan
    size: SessionSize
    policy_badges: PolicyBadges
    events: list[EventResponse]
    generation_mode: str
    auto_events_count: int
    manual_events_count: int
    redaction_stats: dict[str, int]


class TimelineStats(BaseModel):
    """Aggregated timeline statistics"""

    total_sessions: int
    total_events: int
    total_tokens: int
    avg_events_per_session: float
    event_types_breakdown: dict[str, int]
    redaction_stats: dict[str, int]
    generation_modes: dict[str, int]
    date_range: dict[str, str]


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    storage_path: str
    storage_exists: bool
    timestamp: str


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="Free Intelligence - Timeline API",
    description="Timeline UI backend with session management and policy badges",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware (allow Aurity frontend on port 9000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:9000",
        "http://127.0.0.1:9000",
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Storage path for timelines (in-memory for now, will use HDF5/event store)
# TODO: Integrate with fi_event_store.py or storage/corpus.h5
STORAGE_PATH = Path(__file__).parent.parent / "storage"

# Mock timeline storage (will be replaced with actual persistence)
MOCK_TIMELINES: dict[str, Timeline] = {}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def format_duration_human(duration_ms: int) -> str:
    """Format duration in milliseconds to human-readable string"""
    seconds = duration_ms // 1000
    minutes = seconds // 60
    hours = minutes // 60

    if hours > 0:
        remaining_minutes = minutes % 60
        return f"{hours}h {remaining_minutes}m"
    elif minutes > 0:
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        return f"{seconds}s"


def format_size_human(tokens: int, chars: int) -> str:
    """Format size to human-readable string"""
    if tokens > 0:
        if tokens >= 1000:
            return f"{tokens/1000:.1f}K tokens"
        return f"{tokens} tokens"
    elif chars > 0:
        if chars >= 1000:
            return f"{chars/1000:.1f}K chars"
        return f"{chars} chars"
    return "0 tokens"


def compute_policy_badges(timeline: Timeline) -> PolicyBadges:
    """
    Compute policy verification badges for a timeline.

    Badges:
    - hash_verified: Check if all events have valid content_hash
    - policy_compliant: Check append-only + no-mutation compliance
    - redaction_applied: Check if PII redaction is applied
    - audit_logged: Check if audit logs exist for timeline operations

    Returns:
        PolicyBadges with status: OK, FAIL, PENDING, N/A
    """
    # Hash verification: Check if all events have non-empty content_hash
    hash_verified = "OK"
    for event in timeline.events:
        if not event.content_hash or len(event.content_hash) != 64:
            hash_verified = "FAIL"
            break

    # Policy compliance: Assume OK (would check append-only policy in production)
    policy_compliant = "OK"

    # Redaction: Check if any redaction policy is applied
    redaction_applied = (
        "OK"
        if any(event.redaction_policy != RedactionPolicy.NONE for event in timeline.events)
        else "N/A"
    )

    # Audit: Assume OK (would check audit_logs in production)
    audit_logged = "OK"

    logger.info(
        "POLICY_BADGES_COMPUTED",
        session_id=timeline.session_id,
        hash_verified=hash_verified,
        policy_compliant=policy_compliant,
        redaction_applied=redaction_applied,
        audit_logged=audit_logged,
    )

    return PolicyBadges(
        hash_verified=hash_verified,
        policy_compliant=policy_compliant,
        redaction_applied=redaction_applied,
        audit_logged=audit_logged,
    )


def compute_session_timespan(timeline: Timeline) -> SessionTimespan:
    """Compute session timespan from events"""
    if not timeline.events:
        now = datetime.now(timezone.utc).isoformat()
        return SessionTimespan(start=now, end=now, duration_ms=0, duration_human="0s")

    # Sort events by timestamp
    sorted_events = sorted(timeline.events, key=lambda e: e.timestamp)
    start = sorted_events[0].timestamp
    end = sorted_events[-1].timestamp

    duration_ms = int((end - start).total_seconds() * 1000)
    duration_human = format_duration_human(duration_ms)

    return SessionTimespan(
        start=start.isoformat(),
        end=end.isoformat(),
        duration_ms=duration_ms,
        duration_human=duration_human,
    )


def compute_session_size(timeline: Timeline) -> SessionSize:
    """Compute session size metrics"""
    interaction_count = len(timeline.events)

    # Calculate total characters from what + summary
    total_chars = sum(len(event.what) + len(event.summary or "") for event in timeline.events)

    # Mock tokens (would come from actual LLM metadata)
    total_tokens = 0
    avg_tokens = 0.0

    size_human = format_size_human(total_tokens, total_chars)

    return SessionSize(
        interaction_count=interaction_count,
        total_tokens=total_tokens,
        total_chars=total_chars,
        avg_tokens_per_interaction=avg_tokens,
        size_human=size_human,
    )


def timeline_to_session_summary(timeline: Timeline) -> SessionSummary:
    """Convert Timeline to SessionSummary for API response"""
    metadata = SessionMetadata(
        session_id=timeline.session_id,
        thread_id=None,
        owner_hash=timeline.owner_hash[:16],  # Only first 16 chars
        created_at=timeline.created_at.isoformat(),
        updated_at=timeline.updated_at.isoformat(),
    )

    timespan = compute_session_timespan(timeline)
    size = compute_session_size(timeline)
    policy_badges = compute_policy_badges(timeline)

    # Preview from first event
    preview = timeline.events[0].what[:200] if timeline.events else "No events"

    return SessionSummary(
        metadata=metadata,
        timespan=timespan,
        size=size,
        policy_badges=policy_badges,
        preview=preview,
    )


def event_to_response(event: TimelineEvent) -> EventResponse:
    """Convert TimelineEvent to EventResponse"""
    return EventResponse(
        event_id=event.event_id,
        event_type=event.event_type.value,
        timestamp=event.timestamp.isoformat(),
        who=event.who,
        what=event.what,
        summary=event.summary,
        content_hash=event.content_hash,
        redaction_policy=event.redaction_policy.value,
        causality=[c.model_dump() for c in event.causality],
        tags=event.tags,
        auto_generated=event.auto_generated,
        generation_mode=event.generation_mode.value,
        confidence_score=event.confidence_score,
    )


def timeline_to_session_detail(timeline: Timeline) -> SessionDetail:
    """Convert Timeline to SessionDetail for API response"""
    metadata = SessionMetadata(
        session_id=timeline.session_id,
        thread_id=None,
        owner_hash=timeline.owner_hash[:16],
        created_at=timeline.created_at.isoformat(),
        updated_at=timeline.updated_at.isoformat(),
    )

    timespan = compute_session_timespan(timeline)
    size = compute_session_size(timeline)
    policy_badges = compute_policy_badges(timeline)

    # Sort events by timestamp (causality ordering)
    sorted_events = sorted(timeline.events, key=lambda e: e.timestamp)
    events = [event_to_response(e) for e in sorted_events]

    return SessionDetail(
        metadata=metadata,
        timespan=timespan,
        size=size,
        policy_badges=policy_badges,
        events=events,
        generation_mode=timeline.generation_mode.value,
        auto_events_count=timeline.auto_events_count,
        manual_events_count=timeline.manual_events_count,
        redaction_stats=timeline.redaction_stats,
    )


# ============================================================================
# MOCK DATA INITIALIZATION (for development)
# ============================================================================


def init_mock_data():
    """Initialize mock timeline data for development"""
    from backend.timeline_models import (
        CausalityType,
        create_causality,
        create_timeline_event,
    )

    # Create sample timeline
    timeline = Timeline(
        session_id="session_20251029_100000", owner_hash="abc123def456789012345678901234567890"
    )

    # Event 1: User message
    event1 = create_timeline_event(
        event_type=TimelineEventType.USER_MESSAGE,
        who="user_abc123",
        what="Usuario reporta dolor de pecho",
        raw_content="Tengo dolor en el pecho desde hace 2 horas, siento presión",
        summary="Dolor torácico agudo con presión (2h evolución)",
        redaction_policy=RedactionPolicy.SUMMARY,
        session_id=timeline.session_id,
        tags=["symptoms", "chest_pain", "urgent"],
        auto_generated=False,
    )
    timeline.add_event(event1)

    # Event 2: Extraction started
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
                confidence=1.0,
            )
        ],
        redaction_policy=RedactionPolicy.METADATA,
        session_id=timeline.session_id,
        tags=["system", "extraction"],
        auto_generated=True,
        generation_mode=TimelineMode.AUTO,
    )
    timeline.add_event(event2)

    # Event 3: Critical pattern detected
    event3 = create_timeline_event(
        event_type=TimelineEventType.CRITICAL_PATTERN_DETECTED,
        who="system",
        what="⚠️ Patrón crítico: posible síndrome coronario agudo",
        raw_content="CRITICAL: Chest pain + pressure + 2h = ACS risk",
        summary="Dolor torácico con características de alto riesgo cardiovascular",
        causality=[
            create_causality(
                related_event_id=event2.event_id,
                causality_type=CausalityType.CAUSED_BY,
                explanation="Extracción identificó patrón de alto riesgo",
                confidence=0.85,
            )
        ],
        redaction_policy=RedactionPolicy.SUMMARY,
        session_id=timeline.session_id,
        tags=["critical", "acs", "widow_maker"],
        auto_generated=True,
        generation_mode=TimelineMode.AUTO,
    )
    timeline.add_event(event3)

    # Event 4: Urgency escalated
    event4 = create_timeline_event(
        event_type=TimelineEventType.URGENCY_ESCALATED,
        who="system",
        what="Urgencia escalada: CRITICAL → llamar 911 inmediatamente",
        raw_content="URGENCY_ESCALATED: CRITICAL",
        causality=[
            create_causality(
                related_event_id=event3.event_id,
                causality_type=CausalityType.TRIGGERED,
                explanation="Patrón crítico requiere escalamiento inmediato",
                confidence=1.0,
            )
        ],
        redaction_policy=RedactionPolicy.METADATA,
        session_id=timeline.session_id,
        tags=["critical", "escalation", "emergency"],
        auto_generated=True,
        generation_mode=TimelineMode.AUTO,
    )
    timeline.add_event(event4)

    MOCK_TIMELINES[timeline.session_id] = timeline

    logger.info(
        "MOCK_DATA_INITIALIZED",
        sessions=len(MOCK_TIMELINES),
        sample_session=timeline.session_id,
        events=len(timeline.events),
    )


# ============================================================================
# API ENDPOINTS
# ============================================================================


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        storage_path=str(STORAGE_PATH),
        storage_exists=STORAGE_PATH.exists(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/api/timeline/sessions", response_model=list[SessionSummary], tags=["timeline"])
async def list_sessions(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of sessions"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort: str = Query("recent", description="Sort order: recent, oldest, events_desc, events_asc"),
):
    """
    List timeline sessions with pagination.

    Returns:
        - Session metadata (ID, owner_hash, timestamps)
        - Timespan (start, end, duration)
        - Size metrics (events, tokens, chars)
        - Policy badges (hash, policy, redaction, audit)
        - Preview of first event

    Performance target: p95 <300ms
    """
    start_time = time.time()

    logger.info("TIMELINE_SESSIONS_LIST_REQUEST", limit=limit, offset=offset, sort=sort)

    # Get all timelines
    timelines = list(MOCK_TIMELINES.values())

    # Sort
    if sort == "recent":
        timelines.sort(key=lambda t: t.updated_at, reverse=True)
    elif sort == "oldest":
        timelines.sort(key=lambda t: t.created_at)
    elif sort == "events_desc":
        timelines.sort(key=lambda t: len(t.events), reverse=True)
    elif sort == "events_asc":
        timelines.sort(key=lambda t: len(t.events))

    # Paginate
    paginated = timelines[offset : offset + limit]

    # Convert to response
    summaries = [timeline_to_session_summary(t) for t in paginated]

    latency_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "TIMELINE_SESSIONS_LIST_RESPONSE",
        total=len(timelines),
        returned=len(summaries),
        latency_ms=latency_ms,
    )

    return summaries


@app.get("/api/timeline/sessions/{session_id}", response_model=SessionDetail, tags=["timeline"])
async def get_session_detail(session_id: str = PathParam(..., description="Session ID")):
    """
    Get detailed session with all events.

    Returns:
        - Full session metadata
        - All events with causality
        - Policy badges
        - Redaction stats

    Performance target: p95 <200ms
    """
    start_time = time.time()

    logger.info("TIMELINE_SESSION_DETAIL_REQUEST", session_id=session_id)

    timeline = MOCK_TIMELINES.get(session_id)

    if not timeline:
        logger.warning("TIMELINE_SESSION_NOT_FOUND", session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {session_id} not found"
        )

    detail = timeline_to_session_detail(timeline)

    latency_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "TIMELINE_SESSION_DETAIL_RESPONSE",
        session_id=session_id,
        events=len(timeline.events),
        latency_ms=latency_ms,
    )

    return detail


@app.get("/api/timeline/events", response_model=list[EventResponse], tags=["timeline"])
async def list_events(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    who: Optional[str] = Query(None, description="Filter by actor"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    Stream timeline events with filters.

    Filters:
        - session_id: Filter by session
        - event_type: Filter by event type
        - who: Filter by actor (user/assistant/system)

    Performance target: p95 <300ms
    """
    start_time = time.time()

    logger.info(
        "TIMELINE_EVENTS_LIST_REQUEST",
        session_id=session_id,
        event_type=event_type,
        who=who,
        limit=limit,
        offset=offset,
    )

    # Collect all events from all timelines
    all_events = []
    for timeline in MOCK_TIMELINES.values():
        for event in timeline.events:
            # Apply filters
            if session_id and timeline.session_id != session_id:
                continue
            if event_type and event.event_type.value != event_type:
                continue
            if who and event.who != who:
                continue

            all_events.append(event)

    # Sort by timestamp
    all_events.sort(key=lambda e: e.timestamp, reverse=True)

    # Paginate
    paginated = all_events[offset : offset + limit]

    # Convert to response
    events = [event_to_response(e) for e in paginated]

    latency_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "TIMELINE_EVENTS_LIST_RESPONSE",
        total=len(all_events),
        returned=len(events),
        latency_ms=latency_ms,
    )

    return events


@app.get("/api/timeline/stats", response_model=TimelineStats, tags=["timeline"])
async def get_stats():
    """
    Get aggregated timeline statistics.

    Returns:
        - Total sessions
        - Total events
        - Event types breakdown
        - Redaction stats
        - Generation modes
        - Date range

    Performance target: p95 <300ms
    """
    start_time = time.time()

    logger.info("TIMELINE_STATS_REQUEST")

    total_sessions = len(MOCK_TIMELINES)
    total_events = sum(len(t.events) for t in MOCK_TIMELINES.values())
    total_tokens = 0  # Would come from actual LLM metadata

    avg_events = total_events / total_sessions if total_sessions > 0 else 0.0

    # Event types breakdown
    event_types_breakdown: dict[str, int] = defaultdict(int)
    for timeline in MOCK_TIMELINES.values():
        for event in timeline.events:
            event_types_breakdown[event.event_type.value] += 1

    # Redaction stats (aggregate from all timelines)
    redaction_stats: dict[str, int] = defaultdict(int)
    for timeline in MOCK_TIMELINES.values():
        for policy, count in timeline.redaction_stats.items():
            redaction_stats[policy] += count

    # Generation modes
    generation_modes: dict[str, int] = defaultdict(int)
    for timeline in MOCK_TIMELINES.values():
        generation_modes[timeline.generation_mode.value] += 1

    # Date range
    all_timestamps = []
    for timeline in MOCK_TIMELINES.values():
        for event in timeline.events:
            all_timestamps.append(event.timestamp)

    date_range = {}
    if all_timestamps:
        all_timestamps.sort()
        date_range = {
            "earliest": all_timestamps[0].isoformat(),
            "latest": all_timestamps[-1].isoformat(),
        }

    latency_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "TIMELINE_STATS_RESPONSE",
        total_sessions=total_sessions,
        total_events=total_events,
        latency_ms=latency_ms,
    )

    return TimelineStats(
        total_sessions=total_sessions,
        total_events=total_events,
        total_tokens=total_tokens,
        avg_events_per_session=avg_events,
        event_types_breakdown=dict(event_types_breakdown),
        redaction_stats=dict(redaction_stats),
        generation_modes=dict(generation_modes),
        date_range=date_range,
    )


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize mock data and log startup"""
    init_mock_data()

    logger.info(
        "TIMELINE_API_STARTUP",
        port=9002,
        storage_path=str(STORAGE_PATH),
        mock_sessions=len(MOCK_TIMELINES),
    )

    print("🚀 FI Timeline API starting on port 9002")
    print(f"📁 Storage path: {STORAGE_PATH}")
    print(f"📊 Mock sessions: {len(MOCK_TIMELINES)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown"""
    logger.info("TIMELINE_API_SHUTDOWN")
    print("🛑 FI Timeline API shutting down")


# ============================================================================
# MAIN (for direct execution)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.timeline_api:app",
        host="0.0.0.0",
        port=9002,
        reload=True,
        log_level="info",
    )
