"""Event Consumers - Concrete projection implementations.

These projections build materialized views from the event stream:

- SessionIndex: Quick lookup of session metadata
- TranscriptionTimeline: Ordered chunks per session
- AssistantTurns: Chat turns with metadata
- MetricsByType: Event counts and stats by type

Usage:
    from backend.core.infrastructure.events.projections.consumers import (
        SessionIndexProjection,
        TranscriptionTimelineProjection,
    )
    from backend.core.infrastructure.events.projections.registry import get_registry

    registry = get_registry()
    registry.register(SessionIndexProjection())
    registry.register(TranscriptionTimelineProjection())
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import h5py
from backend.utils.common.logging.logger import get_logger
from backend.core.infrastructure.events.domain.events import EventType
from backend.core.infrastructure.events.projections.registry import Projection
from pathlib import Path

if TYPE_CHECKING:
    from backend.core.infrastructure.events.domain.events import DomainEvent

logger = get_logger(__name__)

# Default path for projection storage
DEFAULT_PROJECTIONS_PATH = Path("storage/projections.h5")


class HDF5ProjectionMixin:
    """Mixin for HDF5-backed projection persistence.

    Provides save/load methods for projection state.
    """

    _projection_path: Path = DEFAULT_PROJECTIONS_PATH

    def _ensure_file(self) -> None:
        """Ensure HDF5 file and group exist."""
        self._projection_path.parent.mkdir(parents=True, exist_ok=True)
        with h5py.File(self._projection_path, "a") as f:
            if "projections" not in f:
                f.create_group("projections")

    def _save_state(self, name: str, state: dict[str, Any]) -> None:
        """Save projection state to HDF5.

        Args:
            name: Projection name
            state: State dict to persist
        """
        self._ensure_file()
        with h5py.File(self._projection_path, "a") as f:
            group = f["projections"]

            if name in group:
                del group[name]

            json_str = json.dumps(state, ensure_ascii=False, default=str)
            dt = h5py.special_dtype(vlen=str)
            group.create_dataset(name, data=json_str, dtype=dt)

    def _load_state(self, name: str) -> dict[str, Any] | None:
        """Load projection state from HDF5.

        Args:
            name: Projection name

        Returns:
            State dict or None if not found
        """
        self._ensure_file()
        try:
            with h5py.File(self._projection_path, "r") as f:
                if "projections" not in f:
                    return None

                group = f["projections"]
                if name not in group:
                    return None

                json_str = group[name][()]
                if isinstance(json_str, bytes):
                    json_str = json_str.decode("utf-8")

                return json.loads(json_str)
        except Exception as e:
            logger.warning("PROJECTION_LOAD_FAILED", name=name, error=str(e))
            return None


class SessionIndexProjection(Projection, HDF5ProjectionMixin):
    """Index of all sessions with quick metadata lookup.

    State structure:
    {
        "sessions": {
            "<session_id>": {
                "status": "in_progress|completed|failed",
                "started_at": "...",
                "ended_at": "...",
                "total_chunks": 0,
                "has_soap": false,
                "has_diarization": false,
            }
        },
        "stats": {
            "total_sessions": 0,
            "active_sessions": 0,
            "completed_sessions": 0,
        }
    }
    """

    @property
    def name(self) -> str:
        return "session_index"

    @property
    def subscribed_events(self) -> list[EventType]:
        return [
            EventType.TRANSCRIPTION_STARTED,
            EventType.TRANSCRIPTION_CHUNK_RECEIVED,
            EventType.TRANSCRIPTION_ENDED,
            EventType.TRANSCRIPTION_FAILED,
            EventType.SOAP_GENERATION_COMPLETED,
            EventType.DIARIZATION_COMPLETED,
            EventType.SESSION_FINALIZED,
        ]

    def __init__(self) -> None:
        super().__init__()
        self._sessions: dict[str, dict[str, Any]] = {}
        self._stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "completed_sessions": 0,
        }
        # Load persisted state
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load persisted state."""
        state = self._load_state(self.name)
        if state:
            self._sessions = state.get("sessions", {})
            self._stats = state.get("stats", self._stats)
            logger.info(
                "PROJECTION_LOADED",
                name=self.name,
                sessions=len(self._sessions),
            )

    async def handle(self, event: "DomainEvent") -> None:
        """Process event and update session index."""
        session_id = event.aggregate_id

        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "status": "pending",
                "started_at": None,
                "ended_at": None,
                "total_chunks": 0,
                "has_soap": False,
                "has_diarization": False,
            }
            self._stats["total_sessions"] += 1

        session = self._sessions[session_id]

        if event.event_type == EventType.TRANSCRIPTION_STARTED:
            session["status"] = "in_progress"
            session["started_at"] = event.timestamp.isoformat()
            self._stats["active_sessions"] += 1

        elif event.event_type == EventType.TRANSCRIPTION_CHUNK_RECEIVED:
            session["total_chunks"] += 1

        elif event.event_type == EventType.TRANSCRIPTION_ENDED:
            session["status"] = "completed"
            session["ended_at"] = event.timestamp.isoformat()
            session["total_chunks"] = event.payload.get("total_chunks", session["total_chunks"])
            self._stats["active_sessions"] = max(0, self._stats["active_sessions"] - 1)
            self._stats["completed_sessions"] += 1

        elif event.event_type == EventType.TRANSCRIPTION_FAILED:
            session["status"] = "failed"
            session["ended_at"] = event.timestamp.isoformat()
            self._stats["active_sessions"] = max(0, self._stats["active_sessions"] - 1)

        elif event.event_type == EventType.SOAP_GENERATION_COMPLETED:
            session["has_soap"] = True

        elif event.event_type == EventType.DIARIZATION_COMPLETED:
            session["has_diarization"] = True

        elif event.event_type == EventType.SESSION_FINALIZED:
            session["status"] = "finalized"

        # Persist every 10 events
        if self._state.events_processed % 10 == 0:
            await asyncio.to_thread(self._persist)

    def _persist(self) -> None:
        """Persist state to disk."""
        self._save_state(
            self.name,
            {
                "sessions": self._sessions,
                "stats": self._stats,
            },
        )

    async def get_state(self) -> dict[str, Any]:
        """Get current session index state."""
        return {
            "sessions": self._sessions,
            "stats": self._stats,
            "session_count": len(self._sessions),
        }

    async def reset(self) -> None:
        """Reset to initial state."""
        self._sessions = {}
        self._stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "completed_sessions": 0,
        }

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session metadata by ID."""
        return self._sessions.get(session_id)

    async def list_sessions(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List sessions with optional filtering.

        Args:
            status: Filter by status
            limit: Max results

        Returns:
            List of session dicts with IDs
        """
        results = []
        for sid, session in self._sessions.items():
            if status and session.get("status") != status:
                continue
            results.append({"session_id": sid, **session})
            if len(results) >= limit:
                break
        return results


class TranscriptionTimelineProjection(Projection, HDF5ProjectionMixin):
    """Ordered timeline of transcription chunks per session.

    State structure:
    {
        "<session_id>": {
            "chunks": [
                {"chunk_number": 0, "duration_ms": 100, "timestamp": "..."},
                ...
            ],
            "total_duration_ms": 0,
        }
    }
    """

    @property
    def name(self) -> str:
        return "transcription_timeline"

    @property
    def subscribed_events(self) -> list[EventType]:
        return [
            EventType.TRANSCRIPTION_STARTED,
            EventType.TRANSCRIPTION_CHUNK_RECEIVED,
            EventType.TRANSCRIPTION_ENDED,
        ]

    def __init__(self) -> None:
        super().__init__()
        self._timelines: dict[str, dict[str, Any]] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load persisted state."""
        state = self._load_state(self.name)
        if state:
            self._timelines = state
            logger.info(
                "PROJECTION_LOADED",
                name=self.name,
                sessions=len(self._timelines),
            )

    async def handle(self, event: "DomainEvent") -> None:
        """Process transcription events."""
        session_id = event.aggregate_id

        if session_id not in self._timelines:
            self._timelines[session_id] = {
                "chunks": [],
                "total_duration_ms": 0,
                "status": "pending",
            }

        timeline = self._timelines[session_id]

        if event.event_type == EventType.TRANSCRIPTION_STARTED:
            timeline["status"] = "in_progress"
            timeline["started_at"] = event.timestamp.isoformat()

        elif event.event_type == EventType.TRANSCRIPTION_CHUNK_RECEIVED:
            chunk = {
                "chunk_number": event.payload.get("chunk_number", len(timeline["chunks"])),
                "duration_ms": event.payload.get("duration_ms", 0),
                "audio_size_bytes": event.payload.get("audio_size_bytes", 0),
                "timestamp": event.timestamp.isoformat(),
            }
            timeline["chunks"].append(chunk)
            timeline["total_duration_ms"] += chunk["duration_ms"]

        elif event.event_type == EventType.TRANSCRIPTION_ENDED:
            timeline["status"] = "completed"
            timeline["ended_at"] = event.timestamp.isoformat()

        # Persist periodically
        if self._state.events_processed % 10 == 0:
            await asyncio.to_thread(self._persist)

    def _persist(self) -> None:
        """Persist state to disk."""
        self._save_state(self.name, self._timelines)

    async def get_state(self) -> dict[str, Any]:
        """Get all timelines."""
        return {
            "timelines": self._timelines,
            "session_count": len(self._timelines),
        }

    async def reset(self) -> None:
        """Reset to initial state."""
        self._timelines = {}

    async def get_timeline(self, session_id: str) -> dict[str, Any] | None:
        """Get timeline for a session."""
        return self._timelines.get(session_id)


class AssistantTurnsProjection(Projection, HDF5ProjectionMixin):
    """Chat assistant turns aggregated by session.

    State structure:
    {
        "<session_id>": {
            "turns": [
                {"role": "user|assistant", "token_count": 0, "timestamp": "..."},
                ...
            ],
            "total_tokens": 0,
        }
    }
    """

    @property
    def name(self) -> str:
        return "assistant_turns"

    @property
    def subscribed_events(self) -> list[EventType]:
        return [
            EventType.ASSISTANT_MESSAGE_RECEIVED,
            EventType.ASSISTANT_RESPONSE_GENERATED,
        ]

    def __init__(self) -> None:
        super().__init__()
        self._sessions: dict[str, dict[str, Any]] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load persisted state."""
        state = self._load_state(self.name)
        if state:
            self._sessions = state
            logger.info(
                "PROJECTION_LOADED",
                name=self.name,
                sessions=len(self._sessions),
            )

    async def handle(self, event: "DomainEvent") -> None:
        """Process assistant events."""
        session_id = event.aggregate_id

        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "turns": [],
                "total_tokens": 0,
            }

        session = self._sessions[session_id]
        token_count = event.payload.get("token_count", 0)

        turn = {
            "role": event.payload.get("message_type", "unknown"),
            "token_count": token_count,
            "timestamp": event.timestamp.isoformat(),
        }

        session["turns"].append(turn)
        session["total_tokens"] += token_count

        # Persist periodically
        if self._state.events_processed % 5 == 0:
            await asyncio.to_thread(self._persist)

    def _persist(self) -> None:
        """Persist state to disk."""
        self._save_state(self.name, self._sessions)

    async def get_state(self) -> dict[str, Any]:
        """Get all assistant sessions."""
        return {
            "sessions": self._sessions,
            "session_count": len(self._sessions),
        }

    async def reset(self) -> None:
        """Reset to initial state."""
        self._sessions = {}

    async def get_turns(self, session_id: str) -> list[dict[str, Any]]:
        """Get turns for a session."""
        session = self._sessions.get(session_id)
        return session["turns"] if session else []


class MetricsByTypeProjection(Projection):
    """Aggregate metrics by event type.

    State structure:
    {
        "by_type": {
            "TRANSCRIPTION_STARTED": {"count": 0, "last_at": "..."},
            ...
        },
        "total_events": 0,
        "first_event_at": "...",
        "last_event_at": "...",
    }
    """

    @property
    def name(self) -> str:
        return "metrics_by_type"

    @property
    def subscribed_events(self) -> list[EventType]:
        # Subscribe to ALL event types
        return list(EventType)

    def __init__(self) -> None:
        super().__init__()
        self._by_type: dict[str, dict[str, Any]] = {}
        self._total_events = 0
        self._first_event_at: datetime | None = None
        self._last_event_at: datetime | None = None

    async def handle(self, event: "DomainEvent") -> None:
        """Process any event for metrics."""
        event_type = event.event_type.value

        if event_type not in self._by_type:
            self._by_type[event_type] = {
                "count": 0,
                "first_at": event.timestamp.isoformat(),
                "last_at": None,
            }

        self._by_type[event_type]["count"] += 1
        self._by_type[event_type]["last_at"] = event.timestamp.isoformat()

        self._total_events += 1

        if self._first_event_at is None:
            self._first_event_at = event.timestamp
        self._last_event_at = event.timestamp

    async def get_state(self) -> dict[str, Any]:
        """Get metrics state."""
        return {
            "by_type": self._by_type,
            "total_events": self._total_events,
            "first_event_at": (self._first_event_at.isoformat() if self._first_event_at else None),
            "last_event_at": (self._last_event_at.isoformat() if self._last_event_at else None),
            "event_types_seen": len(self._by_type),
        }

    async def reset(self) -> None:
        """Reset to initial state."""
        self._by_type = {}
        self._total_events = 0
        self._first_event_at = None
        self._last_event_at = None

    async def get_type_stats(self, event_type: str) -> dict[str, Any] | None:
        """Get stats for a specific event type."""
        return self._by_type.get(event_type)


# ============================================================================
# HELPERS
# ============================================================================


def register_default_projections() -> None:
    """Register all default projections with the global registry."""
    from backend.core.infrastructure.events.projections.registry import get_registry

    registry = get_registry()

    # Register all projections
    registry.register(SessionIndexProjection())
    registry.register(TranscriptionTimelineProjection())
    registry.register(AssistantTurnsProjection())
    registry.register(MetricsByTypeProjection())

    logger.info("DEFAULT_PROJECTIONS_REGISTERED", count=4)
