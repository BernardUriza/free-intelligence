"""HDF5MemoryStore - Concrete implementation of IMemoryStore for audio transcriptions.

Extracts audio transcription storage logic from DIMemoryService (Phase 2.4 - Memory DI).

Author: Claude Sonnet 4.5
Created: 2026-01-31
Card: DI Refactor Phase 2.4 - Memory Service DI
"""

from __future__ import annotations

import h5py
from datetime import datetime

from backend.repositories.interfaces.imemory_store import (
    IMemoryStore,
    AudioEventDict,
    AudioStatsDict,
)
from backend.infrastructure.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger


class HDF5MemoryStore(IMemoryStore):
    """HDF5-based implementation of IMemoryStore for audio transcription storage.

    Responsibilities:
    - Read audio transcription chunks from HDF5 corpus (sessions/tasks/TRANSCRIPTION/chunks)
    - Filter by doctor_id for multi-tenancy security
    - Search transcriptions by text query
    - Provide statistics (count, timestamps, unique sessions)

    HDF5 Structure:
        corpus.h5/
        └── sessions/
            └── {session_id}/
                ├── attrs: doctor_id (or owner_id or user_id)
                └── tasks/
                    └── TRANSCRIPTION/
                        └── chunks/
                            └── chunk_{N}/
                                ├── transcript (dataset)
                                ├── created_at (dataset)
                                ├── duration (dataset, optional)
                                ├── confidence_score (dataset, optional)
                                ├── language (dataset, optional)
                                └── stt_provider (dataset, optional)

    Security:
    - ALL methods filter by doctor_id (prevent cross-doctor access)
    - Sessions without owner metadata are excluded (legacy data protection)
    """

    def __init__(self, corpus_path: str, logger: ILogger | None = None):
        """Initialize HDF5MemoryStore.

        Args:
            corpus_path: Path to HDF5 corpus file
            logger: Logger instance (optional, defaults to module logger)
        """
        self.corpus_path = corpus_path
        self.logger = logger or get_logger(__name__)

    def get_audio_events(
        self,
        doctor_id: str,
        start_ts: int | None = None,
        end_ts: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AudioEventDict], int]:
        """Fetch audio transcription events for a doctor.

        Extracts from DIMemoryService._get_audio_events() (lines 191-361).

        Args:
            doctor_id: Doctor identifier (Auth0 user.sub)
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
        """
        events: list[AudioEventDict] = []

        try:
            with h5py.File(self.corpus_path, "r") as f:
                if "sessions" not in f:
                    return [], 0

                sessions_group = f["sessions"]

                # Collect all chunks with timestamps
                all_chunks: list[tuple[int, AudioEventDict]] = []  # (timestamp, event_dict)

                for session_id in sessions_group:
                    try:
                        session = sessions_group[session_id]

                        # SECURITY: Check session ownership (doctor_id/owner_id/user_id)
                        session_owner = self._get_session_owner(session)

                        if session_owner is None:
                            # Legacy session without owner - skip for security
                            self.logger.debug(
                                "AUDIO_SESSION_NO_OWNER",
                                session_id=session_id,
                                action="skipped",
                                reason="No owner metadata - security isolation",
                            )
                            continue

                        if session_owner != doctor_id:
                            continue  # Skip - not owned by this doctor

                        # Navigate to transcription chunks
                        if "tasks" not in session:  # type: ignore[operator]
                            continue

                        tasks = session["tasks"]
                        if "TRANSCRIPTION" not in tasks:  # type: ignore[operator]
                            continue

                        trans_task = tasks["TRANSCRIPTION"]
                        if "chunks" not in trans_task:  # type: ignore[operator]
                            continue

                        chunks_group = trans_task["chunks"]

                        for chunk_name in chunks_group:
                            chunk = chunks_group[chunk_name]

                            # Get timestamp from created_at
                            created_at = self._read_dataset_str(chunk, "created_at")
                            if not created_at:
                                continue

                            ts = self._parse_timestamp(created_at)

                            # Apply time range filter early
                            if start_ts and ts < start_ts:
                                continue
                            if end_ts and ts > end_ts:
                                continue

                            # Build AudioEventDict
                            event_dict: AudioEventDict = {
                                "session_id": session_id,
                                "chunk_number": self._extract_chunk_number(chunk_name),
                                "transcript": self._read_dataset_str(chunk, "transcript") or "",
                                "timestamp": ts,
                                "created_at": created_at,
                            }

                            # Optional fields
                            duration = self._read_dataset_float(chunk, "duration")
                            if duration is not None:
                                event_dict["duration"] = duration

                            confidence = self._read_dataset_float(chunk, "confidence_score")
                            if confidence is not None:
                                event_dict["confidence"] = confidence

                            language = self._read_dataset_str(chunk, "language")
                            if language:
                                event_dict["language"] = language

                            stt_provider = self._read_dataset_str(chunk, "stt_provider")
                            if stt_provider:
                                event_dict["stt_provider"] = stt_provider

                            all_chunks.append((ts, event_dict))

                    except Exception as e:
                        self.logger.warning(
                            "AUDIO_SESSION_READ_ERROR",
                            session_id=session_id,
                            error=str(e),
                        )
                        continue  # Skip broken session, continue with others

                # Sort by timestamp (newest first)
                all_chunks.sort(key=lambda x: x[0], reverse=True)
                total_count = len(all_chunks)

                # Apply pagination
                paginated = all_chunks[offset : offset + limit]
                events = [event_dict for _, event_dict in paginated]

                return events, total_count

        except Exception as e:
            self.logger.error("AUDIO_EVENTS_FETCH_ERROR", error=str(e), exc_info=True)
            return [], 0

    def search_audio_events(
        self,
        doctor_id: str,
        query: str,
        limit: int = 1000,
    ) -> list[AudioEventDict]:
        """Search audio transcriptions by text query.

        Extracts from DIMemoryService.search_memory() audio portion (lines 545-606).

        Args:
            doctor_id: Doctor identifier
            query: Search query (case-insensitive substring match)
            limit: Maximum results to return (default: 1000 for broad search)

        Returns:
            List of matching audio events (unsorted, unpaginated).
            Caller is responsible for sorting and pagination.

        Security:
            MUST filter by doctor_id. Sessions without owner metadata MUST be excluded.

        Note:
            Uses case-insensitive substring matching (not full-text search).
            For production, consider using vector search or Elasticsearch.
        """
        query_lower = query.lower()
        matching_events: list[AudioEventDict] = []

        try:
            with h5py.File(self.corpus_path, "r") as f:
                if "sessions" not in f:
                    return []

                sessions_group = f["sessions"]

                for session_id in sessions_group:
                    try:
                        session = sessions_group[session_id]

                        # SECURITY: Check session ownership
                        session_owner = self._get_session_owner(session)

                        if session_owner is None or session_owner != doctor_id:
                            continue  # Skip - not owned by this doctor

                        # Navigate to transcription chunks
                        if "tasks" not in session:  # type: ignore[operator]
                            continue

                        tasks = session["tasks"]
                        if "TRANSCRIPTION" not in tasks:  # type: ignore[operator]
                            continue

                        trans_task = tasks["TRANSCRIPTION"]
                        if "chunks" not in trans_task:  # type: ignore[operator]
                            continue

                        chunks_group = trans_task["chunks"]

                        for chunk_name in chunks_group:
                            chunk = chunks_group[chunk_name]

                            # Read transcript and check if query matches
                            transcript = self._read_dataset_str(chunk, "transcript")
                            if not transcript or query_lower not in transcript.lower():
                                continue

                            # Match found - build AudioEventDict
                            created_at = self._read_dataset_str(chunk, "created_at") or ""
                            ts = self._parse_timestamp(created_at) if created_at else 0

                            event_dict: AudioEventDict = {
                                "session_id": session_id,
                                "chunk_number": self._extract_chunk_number(chunk_name),
                                "transcript": transcript,
                                "timestamp": ts,
                                "created_at": created_at,
                            }

                            # Optional fields
                            duration = self._read_dataset_float(chunk, "duration")
                            if duration is not None:
                                event_dict["duration"] = duration

                            confidence = self._read_dataset_float(chunk, "confidence_score")
                            if confidence is not None:
                                event_dict["confidence"] = confidence

                            language = self._read_dataset_str(chunk, "language")
                            if language:
                                event_dict["language"] = language

                            stt_provider = self._read_dataset_str(chunk, "stt_provider")
                            if stt_provider:
                                event_dict["stt_provider"] = stt_provider

                            matching_events.append(event_dict)

                            # Early exit if limit reached
                            if len(matching_events) >= limit:
                                return matching_events

                    except Exception as e:
                        self.logger.warning(
                            "AUDIO_SEARCH_SESSION_ERROR",
                            session_id=session_id,
                            error=str(e),
                        )
                        continue

                return matching_events

        except Exception as e:
            self.logger.warning("AUDIO_SEARCH_ERROR", error=str(e))
            return []

    def get_audio_stats(
        self,
        doctor_id: str,
    ) -> AudioStatsDict:
        """Get statistics for audio transcriptions.

        Extracts from DIMemoryService.get_stats() audio portion (lines 660-714).

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
        """
        audio_count = 0
        all_timestamps: list[int] = []
        unique_sessions: set[str] = set()

        try:
            with h5py.File(self.corpus_path, "r") as f:
                if "sessions" not in f:
                    return {
                        "count": 0,
                        "oldest_timestamp": None,
                        "newest_timestamp": None,
                        "unique_sessions": 0,
                    }

                sessions_group = f["sessions"]

                for session_id in sessions_group:
                    try:
                        session = sessions_group[session_id]

                        # SECURITY: Check session ownership
                        session_owner = self._get_session_owner(session)

                        if session_owner is None or session_owner != doctor_id:
                            continue  # Skip - not owned by this doctor

                        unique_sessions.add(session_id)

                        # Navigate to transcription chunks
                        if "tasks" not in session:  # type: ignore[operator]
                            continue

                        tasks = session["tasks"]
                        if "TRANSCRIPTION" not in tasks:  # type: ignore[operator]
                            continue

                        trans_task = tasks["TRANSCRIPTION"]
                        if "chunks" not in trans_task:  # type: ignore[operator]
                            continue

                        chunks_group = trans_task["chunks"]
                        audio_count += len(chunks_group.keys())

                        # Collect timestamps for oldest/newest
                        for chunk_name in chunks_group:
                            chunk = chunks_group[chunk_name]
                            created_at = self._read_dataset_str(chunk, "created_at")
                            if created_at:
                                ts = self._parse_timestamp(created_at)
                                all_timestamps.append(ts)

                    except Exception:
                        continue  # Skip broken session

        except Exception:
            pass  # Fail silently, return what we have

        # Calculate oldest/newest from collected timestamps
        oldest_ts = min(all_timestamps) if all_timestamps else None
        newest_ts = max(all_timestamps) if all_timestamps else None

        return {
            "count": audio_count,
            "oldest_timestamp": oldest_ts,
            "newest_timestamp": newest_ts,
            "unique_sessions": len(unique_sessions),
        }

    # ============================================================================
    # Helper Methods (extracted from DIMemoryService)
    # ============================================================================

    def _get_session_owner(self, session: h5py.Group) -> str | None:
        """Extract session owner from HDF5 attrs (doctor_id/owner_id/user_id).

        Args:
            session: HDF5 session group

        Returns:
            Owner ID string, or None if no owner metadata found
        """
        session_owner = None

        if "doctor_id" in session.attrs:
            session_owner = session.attrs["doctor_id"]
        elif "owner_id" in session.attrs:
            session_owner = session.attrs["owner_id"]
        elif "user_id" in session.attrs:
            session_owner = session.attrs["user_id"]

        # Decode bytes to string if needed
        if session_owner is not None and isinstance(session_owner, bytes):
            session_owner = session_owner.decode("utf-8")

        return session_owner

    def _read_dataset_str(self, group: h5py.Group, key: str) -> str | None:
        """Read string dataset from HDF5 group.

        Args:
            group: HDF5 group
            key: Dataset key

        Returns:
            String value, or None if dataset doesn't exist or isn't a Dataset
        """
        if key not in group:  # type: ignore[operator]
            return None

        ds = group[key]
        if not isinstance(ds, h5py.Dataset):
            return None

        value = ds[()]
        if isinstance(value, bytes):
            return value.decode("utf-8")

        return str(value) if value is not None else None

    def _read_dataset_float(self, group: h5py.Group, key: str) -> float | None:
        """Read float dataset from HDF5 group.

        Args:
            group: HDF5 group
            key: Dataset key

        Returns:
            Float value, or None if dataset doesn't exist or isn't a Dataset
        """
        if key not in group:  # type: ignore[operator]
            return None

        ds = group[key]
        if not isinstance(ds, h5py.Dataset):
            return None

        try:
            return float(ds[()])
        except (ValueError, TypeError):
            return None

    def _extract_chunk_number(self, chunk_name: str) -> int:
        """Extract chunk number from chunk name (e.g., 'chunk_0' → 0).

        Args:
            chunk_name: HDF5 chunk key (e.g., 'chunk_0')

        Returns:
            Chunk number (int), or 0 if parsing fails
        """
        try:
            return int(chunk_name.split("_")[1])
        except (IndexError, ValueError):
            return 0

    def _parse_timestamp(self, timestamp_str: str) -> int:
        """Parse ISO 8601 timestamp string to Unix seconds.

        Args:
            timestamp_str: ISO 8601 timestamp (e.g., '2026-01-31T12:00:00Z')

        Returns:
            Unix timestamp (seconds since epoch)
        """
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return int(dt.timestamp())
        except Exception:
            return 0


__all__ = ["HDF5MemoryStore"]
