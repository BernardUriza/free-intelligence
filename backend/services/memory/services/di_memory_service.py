"""Memory Service - Dependency Injection version.

REFACTORED: Uses IMemoryStore interface for HDF5 access (Phase 2.4 - Memory DI).
Handles longitudinal memory (chat + audio transcriptions).

Author: Claude Code (extracted from longitudinal_memory.py)
Created: 2026-01-28
Updated: 2026-01-31 (Phase 2.4 - IMemoryStore interface injection)
Card: Backend Refactor Phase 2.4 - Memory Service DI
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from backend.repositories.interfaces.imemory_store import IMemoryStore, AudioEventDict
from backend.services.llm.services.conversation_memory import get_memory_manager
from backend.infrastructure.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger


# ============================================================================
# Configuration
# ============================================================================


class TimelineConfig:
    """Centralized configuration for timeline limits."""

    DEFAULT_LIMIT: int = 50
    MAX_LIMIT: int = 200
    DEFAULT_WINDOW_HOURS: int = 24 * 7  # 1 week default
    MAX_WINDOW_DAYS: int = 365  # 1 year max


# ============================================================================
# Data Models (internal)
# ============================================================================


class MemoryEvent:
    """Single event in the unified timeline."""

    def __init__(
        self,
        id: str,
        timestamp: int,
        event_type: Literal["chat_user", "chat_assistant", "transcription"],
        content: str,
        source: Literal["chat", "audio"],
        session_id: str | None = None,
        persona: str | None = None,
        chunk_number: int | None = None,
        duration: float | None = None,
        confidence: float | None = None,
        language: str | None = None,
        stt_provider: str | None = None,
    ):
        self.id = id
        self.timestamp = timestamp
        self.event_type = event_type
        self.content = content
        self.source = source
        self.session_id = session_id
        self.persona = persona
        self.chunk_number = chunk_number
        self.duration = duration
        self.confidence = confidence
        self.language = language
        self.stt_provider = stt_provider

    def to_dict(self) -> dict:
        """Convert to dict for API response."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "content": self.content,
            "source": self.source,
            "session_id": self.session_id,
            "persona": self.persona,
            "chunk_number": self.chunk_number,
            "duration": self.duration,
            "confidence": self.confidence,
            "language": self.language,
            "stt_provider": self.stt_provider,
        }


# ============================================================================
# Memory Service with DI
# ============================================================================


class DIMemoryService:
    """Memory service with Dependency Injection.

    Handles longitudinal memory combining chat messages and audio transcriptions.
    Philosophy: "No existen sesiones. Solo una conversación infinita."

    Dependencies:
    - IMemoryStore (required) - Abstracts audio transcription storage
    - ILogger (optional)

    Clean Architecture:
    - DIMemoryService (business logic) → IMemoryStore (interface) → HDF5MemoryStore (implementation)
    """

    def __init__(
        self,
        memory_store: IMemoryStore,
        logger: ILogger | None = None,
    ):
        """Initialize memory service with dependencies.

        Args:
            memory_store: Memory store implementation (e.g., HDF5MemoryStore)
            logger: Logger instance (defaults to module logger)
        """
        self.memory_store = memory_store
        self.logger = logger or get_logger(__name__)

    def _parse_timestamp(self, ts: str | int | float) -> int:
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
        self,
        doctor_id: str,
        start_ts: int | None,
        end_ts: int | None,
        limit: int,
        offset: int,
    ) -> tuple[list[MemoryEvent], int]:
        """Fetch chat events from conversation memory."""
        events: list[MemoryEvent] = []

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
                    MemoryEvent(
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
            self.logger.warning("CHAT_EVENTS_FETCH_ERROR", doctor_id=doctor_id, error=str(e))
            return [], 0

    def _get_audio_events(
        self,
        doctor_id: str,
        start_ts: int | None,
        end_ts: int | None,
        limit: int,
        offset: int,
    ) -> tuple[list[MemoryEvent], int]:
        """Fetch audio transcription events via IMemoryStore.

        Security: Filters events by doctor_id (delegated to memory_store).
        """
        try:
            # Delegate to memory_store
            audio_event_dicts, total_count = self.memory_store.get_audio_events(
                doctor_id=doctor_id,
                start_ts=start_ts,
                end_ts=end_ts,
                limit=limit,
                offset=offset,
            )

            # Convert AudioEventDict → MemoryEvent
            events: list[MemoryEvent] = []
            for event_dict in audio_event_dicts:
                events.append(
                    MemoryEvent(
                        id=f"audio-{event_dict['session_id']}-{event_dict['chunk_number']}",
                        timestamp=event_dict["timestamp"],
                        event_type="transcription",
                        content=event_dict["transcript"],
                        source="audio",
                        session_id=event_dict["session_id"],
                        chunk_number=event_dict.get("chunk_number"),
                        duration=event_dict.get("duration"),
                        confidence=event_dict.get("confidence"),
                        language=event_dict.get("language"),
                        stt_provider=event_dict.get("stt_provider"),
                    )
                )

            return events, total_count

        except Exception as e:
            self.logger.error("AUDIO_EVENTS_FETCH_ERROR", error=str(e), exc_info=True)
            return [], 0

    async def get_longitudinal_memory(
        self,
        doctor_id: str,
        offset: int,
        limit: int,
        event_type: str,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict:
        """Get longitudinal memory combining chat messages and audio transcriptions.

        Args:
            doctor_id: Doctor identifier (Auth0 user.sub)
            offset: Number of events to skip for pagination
            limit: Maximum events to return
            event_type: Filter by "all", "chat", or "audio"
            start_time: Optional start of time range
            end_time: Optional end of time range

        Returns:
            Dict with keys: events, total, has_more, offset, limit, chat_count, audio_count, time_range
        """
        self.logger.info(
            "LONGITUDINAL_MEMORY_REQUEST",
            doctor_id=doctor_id,
            offset=offset,
            limit=limit,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
        )

        # Audit log for HIPAA compliance
        self.logger.info(
            "PHI_ACCESS",
            doctor_id=doctor_id,
            action="VIEW_TIMELINE",
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
        )

        # Parse time range
        start_ts: int | None = None
        end_ts: int | None = None

        if start_time:
            start_ts = self._parse_timestamp(start_time)
        if end_time:
            end_ts = self._parse_timestamp(end_time)

        # Fetch events based on filter
        chat_events: list[MemoryEvent] = []
        audio_events: list[MemoryEvent] = []
        chat_total = 0
        audio_total = 0

        if event_type in ("all", "chat"):
            chat_events, chat_total = self._get_chat_events(
                doctor_id=doctor_id,
                start_ts=start_ts,
                end_ts=end_ts,
                limit=limit,
                offset=0 if event_type == "all" else offset,
            )

        if event_type in ("all", "audio"):
            audio_events, audio_total = self._get_audio_events(
                doctor_id=doctor_id,
                start_ts=start_ts,
                end_ts=end_ts,
                limit=limit,
                offset=0 if event_type == "all" else offset,
            )

        # Merge and sort
        all_events = chat_events + audio_events
        all_events.sort(key=lambda e: e.timestamp, reverse=True)

        # Apply pagination to merged result
        if event_type == "all":
            all_events = all_events[offset : offset + limit]

        total = (
            chat_total + audio_total
            if event_type == "all"
            else (chat_total if event_type == "chat" else audio_total)
        )

        self.logger.info(
            "LONGITUDINAL_MEMORY_SUCCESS",
            doctor_id=doctor_id,
            returned=len(all_events),
            chat_count=len([e for e in all_events if e.source == "chat"]),
            audio_count=len([e for e in all_events if e.source == "audio"]),
            total=total,
        )

        return {
            "events": [e.to_dict() for e in all_events],
            "total": total,
            "has_more": (offset + len(all_events)) < total,
            "offset": offset,
            "limit": limit,
            "chat_count": len([e for e in all_events if e.source == "chat"]),
            "audio_count": len([e for e in all_events if e.source == "audio"]),
            "time_range": {
                "start": start_time,
                "end": end_time,
                "start_ts": start_ts,
                "end_ts": end_ts,
            },
        }

    async def search_memory(
        self,
        doctor_id: str,
        query: str,
        limit: int,
        offset: int,
    ) -> dict:
        """Search longitudinal memory by text query.

        Uses case-insensitive substring matching across content.

        Args:
            doctor_id: Doctor identifier
            query: Search query string
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            Dict with keys: events, total, has_more, offset, limit, chat_count, audio_count
        """
        self.logger.info(
            "MEMORY_SEARCH_REQUEST",
            doctor_id=doctor_id,
            query=query,
            limit=limit,
            offset=offset,
        )

        # Audit log for HIPAA compliance
        self.logger.info(
            "PHI_ACCESS",
            doctor_id=doctor_id,
            action="SEARCH_TIMELINE",
            query_length=len(query),
            timestamp=datetime.utcnow().isoformat(),
        )

        query_lower = query.lower()
        matching_events: list[MemoryEvent] = []

        # Search chat messages
        try:
            memory = get_memory_manager(doctor_id)
            result = memory.get_paginated_history(
                offset=0,
                limit=1000,  # Search larger window
                session_id=None,
            )

            for idx, interaction in enumerate(result["interactions"]):
                # Check if query matches in content (case-insensitive)
                if query_lower in interaction.content.lower():
                    event_type: Literal["chat_user", "chat_assistant"] = (
                        "chat_user" if interaction.role == "user" else "chat_assistant"
                    )
                    matching_events.append(
                        MemoryEvent(
                            id=f"chat_{interaction.role}_{interaction.timestamp}_{idx}",
                            timestamp=interaction.timestamp,
                            event_type=event_type,
                            content=interaction.content,
                            source="chat",
                            session_id=interaction.session_id,
                            persona=interaction.persona if interaction.role == "assistant" else None,
                        )
                    )
        except Exception as e:
            self.logger.warning("CHAT_SEARCH_ERROR", error=str(e))

        # Search audio transcriptions
        try:
            # Delegate to memory_store (returns unsorted list, no pagination)
            audio_event_dicts = self.memory_store.search_audio_events(
                doctor_id=doctor_id,
                query=query,
                limit=1000,  # Search larger window
            )

            # Convert AudioEventDict → MemoryEvent
            for event_dict in audio_event_dicts:
                matching_events.append(
                    MemoryEvent(
                        id=f"audio_{event_dict['session_id']}_chunk_{event_dict['chunk_number']}",
                        timestamp=event_dict["timestamp"],
                        event_type="transcription",
                        content=event_dict["transcript"],
                        source="audio",
                        session_id=event_dict["session_id"],
                        chunk_number=event_dict.get("chunk_number"),
                        duration=event_dict.get("duration"),
                        confidence=event_dict.get("confidence"),
                        language=event_dict.get("language"),
                        stt_provider=event_dict.get("stt_provider"),
                    )
                )
        except Exception as e:
            self.logger.warning("AUDIO_SEARCH_ERROR", error=str(e))

        # Sort by timestamp (newest first)
        matching_events.sort(key=lambda e: e.timestamp, reverse=True)

        # Apply pagination
        total = len(matching_events)
        paginated = matching_events[offset : offset + limit]

        self.logger.info(
            "MEMORY_SEARCH_SUCCESS",
            doctor_id=doctor_id,
            query=query,
            total_matches=total,
            returned=len(paginated),
        )

        return {
            "events": [e.to_dict() for e in paginated],
            "total": total,
            "has_more": (offset + len(paginated)) < total,
            "offset": offset,
            "limit": limit,
            "chat_count": len([e for e in paginated if e.source == "chat"]),
            "audio_count": len([e for e in paginated if e.source == "audio"]),
            "time_range": {"start": None, "end": None, "start_ts": None, "end_ts": None},
        }

    async def get_stats(self, doctor_id: str) -> dict:
        """Get statistics for the longitudinal memory.

        Args:
            doctor_id: Doctor identifier

        Returns:
            Dict with keys: total_events, chat_messages, audio_transcriptions,
                           oldest_timestamp, newest_timestamp, unique_sessions
        """
        self.logger.info("MEMORY_STATS_REQUEST", doctor_id=doctor_id)

        chat_count = 0
        audio_count = 0
        oldest_ts: int | None = None
        newest_ts: int | None = None
        unique_audio_sessions = 0

        # Chat stats
        try:
            memory = get_memory_manager(doctor_id)
            stats = memory.get_stats()
            chat_count = stats.get("total_interactions", 0)
        except Exception as e:
            self.logger.warning(
                "CHAT_STATS_ERROR",
                doctor_id=doctor_id,
                error=str(e),
            )
            # Continue with audio stats even if chat fails

        # Audio stats - SECURITY: filter by doctor_id (delegated to memory_store)
        try:
            audio_stats_dict = self.memory_store.get_audio_stats(doctor_id=doctor_id)
            audio_count = audio_stats_dict["count"]
            oldest_ts = audio_stats_dict["oldest_timestamp"]
            newest_ts = audio_stats_dict["newest_timestamp"]
            unique_audio_sessions = audio_stats_dict["unique_sessions"]

        except IOError as e:
            # File not accessible (temporary) - return partial stats (chat only)
            self.logger.warning(
                "AUDIO_STATS_UNAVAILABLE",
                doctor_id=doctor_id,
                error=str(e),
                reason="HDF5 file not accessible (temporary)",
            )
            # audio_count remains 0, oldest_ts/newest_ts remain None

        except ValueError as e:
            # Corrupted data (critical) - propagate to caller (HTTP 500)
            self.logger.error(
                "AUDIO_STATS_CORRUPTED",
                doctor_id=doctor_id,
                error=str(e),
            )
            # Re-raise as RuntimeError for FastAPI to handle
            raise RuntimeError(f"Audio transcription data is corrupted: {e}") from e

        return {
            "total_events": chat_count + audio_count,
            "chat_messages": chat_count,
            "audio_transcriptions": audio_count,
            "oldest_timestamp": oldest_ts,
            "newest_timestamp": newest_ts,
            "unique_sessions": unique_audio_sessions,  # Audio sessions (chat tracked separately)
        }
