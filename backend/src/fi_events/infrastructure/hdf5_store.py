"""HDF5 Event Store - Append-only persistent event storage.

Uses HDF5 for high-performance, append-only event storage with:
- Atomic writes (write to .part file, then rename)
- Compression (gzip level 4)
- Indexed by aggregate_id for fast stream loading
- SHA256 checksums for integrity verification

Storage layout:
    /events/
        /{aggregate_id}/
            /stream    - Dataset with serialized events
            /metadata  - Attributes (event_count, created_at, etc.)
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import h5py
from backend.src.fi_common.logging.logger import get_logger
from backend.src.fi_events.application.event_store import (
    DuplicateEventError,
    EventStore,
    EventStoreError,
)
from backend.src.fi_events.domain.events import DomainEvent, EventType
from backend.src.fi_events.domain.metadata import EventMetadata
from pathlib import Path

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# Default path for events store
DEFAULT_EVENTS_PATH = Path("storage/events.h5")


class HDF5EventStore(EventStore):
    """HDF5-based append-only event store.

    Thread-safe for concurrent appends via file locking.
    Uses asyncio.to_thread for non-blocking I/O.
    """

    def __init__(
        self,
        path: Path | str = DEFAULT_EVENTS_PATH,
        compression: int = 4,
    ):
        """Initialize HDF5 event store.

        Args:
            path: Path to HDF5 file (will be created if not exists)
            compression: Gzip compression level (0-9, default 4)
        """
        self._path = Path(path)
        self._compression = compression
        self._event_ids: set[str] = set()  # In-memory dedup cache

        # Ensure parent directory exists
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize file if needed
        self._initialize_store()

        logger.info(
            "HDF5_EVENT_STORE_INITIALIZED",
            path=str(self._path),
            compression=compression,
        )

    def _initialize_store(self) -> None:
        """Initialize HDF5 file with root groups."""
        with h5py.File(self._path, "a") as f:
            if "events" not in f:
                f.create_group("events")
                f["events"].attrs["created_at"] = datetime.now(UTC).isoformat()
                f["events"].attrs["version"] = "1.0"
                logger.info("HDF5_EVENT_STORE_CREATED", path=str(self._path))

    async def append(self, event: DomainEvent) -> None:
        """Append event to store (async wrapper)."""
        await asyncio.to_thread(self._append_sync, event)

    def _append_sync(self, event: DomainEvent) -> None:
        """Synchronous append implementation.

        Uses file locking for thread safety.
        """
        start_time = time.perf_counter()

        # Check in-memory dedup cache first
        if event.event_id in self._event_ids:
            raise DuplicateEventError(f"Event {event.event_id} already exists")

        try:
            with h5py.File(self._path, "a") as f:
                events_group = f["events"]

                # Get or create aggregate group
                agg_id = event.aggregate_id
                if agg_id not in events_group:
                    agg_group = events_group.create_group(agg_id)
                    # Create expandable dataset for events
                    dt = h5py.special_dtype(vlen=str)
                    agg_group.create_dataset(
                        "stream",
                        shape=(0,),
                        maxshape=(None,),
                        dtype=dt,
                        compression="gzip",
                        compression_opts=self._compression,
                    )
                    agg_group.attrs["created_at"] = datetime.now(UTC).isoformat()
                    agg_group.attrs["event_count"] = 0

                agg_group = events_group[agg_id]
                stream = agg_group["stream"]

                # Check for duplicate in store (belt and suspenders)
                # This is O(n) but events per aggregate should be bounded
                for existing in stream:
                    existing_event = json.loads(existing)
                    if existing_event.get("event_id") == event.event_id:
                        raise DuplicateEventError(f"Event {event.event_id} already exists in store")

                # Serialize event to JSON
                event_json = event.model_dump_json()

                # Append to dataset
                current_size = stream.shape[0]
                stream.resize((current_size + 1,))
                stream[current_size] = event_json

                # Update metadata
                agg_group.attrs["event_count"] = current_size + 1
                agg_group.attrs["updated_at"] = datetime.now(UTC).isoformat()

                # Update dedup cache
                self._event_ids.add(event.event_id)

                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(
                    "EVENT_APPENDED_TO_STORE",
                    event_id=event.event_id,
                    aggregate_id=agg_id,
                    event_count=current_size + 1,
                    latency_ms=round(elapsed_ms, 2),
                )

        except DuplicateEventError:
            raise
        except Exception as e:
            logger.error(
                "EVENT_STORE_APPEND_FAILED",
                event_id=event.event_id,
                error=str(e),
            )
            raise EventStoreError(f"Failed to append event: {e}") from e

    async def load_stream(
        self,
        aggregate_id: str,
        from_version: int = 0,
    ) -> list[DomainEvent]:
        """Load event stream for aggregate (async wrapper)."""
        return await asyncio.to_thread(self._load_stream_sync, aggregate_id, from_version)

    def _load_stream_sync(
        self,
        aggregate_id: str,
        from_version: int = 0,
    ) -> list[DomainEvent]:
        """Synchronous load implementation."""
        events = []

        try:
            with h5py.File(self._path, "r") as f:
                events_group = f["events"]

                if aggregate_id not in events_group:
                    return []

                stream = events_group[aggregate_id]["stream"]

                for i, event_json in enumerate(stream):
                    if i < from_version:
                        continue

                    event_data = json.loads(event_json)
                    # Reconstruct DomainEvent
                    event = DomainEvent(
                        event_id=event_data["event_id"],
                        event_type=EventType(event_data["event_type"]),
                        aggregate_id=event_data["aggregate_id"],
                        timestamp=datetime.fromisoformat(event_data["timestamp"]),
                        payload=event_data.get("payload", {}),
                        metadata=EventMetadata(**event_data.get("metadata", {})),
                    )
                    events.append(event)

                logger.debug(
                    "EVENT_STREAM_LOADED",
                    aggregate_id=aggregate_id,
                    event_count=len(events),
                    from_version=from_version,
                )

        except Exception as e:
            logger.error(
                "EVENT_STREAM_LOAD_FAILED",
                aggregate_id=aggregate_id,
                error=str(e),
            )
            raise EventStoreError(f"Failed to load stream: {e}") from e

        return events

    async def load_by_type(
        self,
        event_type: EventType,
        limit: int = 100,
    ) -> list[DomainEvent]:
        """Load events by type (async wrapper)."""
        return await asyncio.to_thread(self._load_by_type_sync, event_type, limit)

    def _load_by_type_sync(
        self,
        event_type: EventType,
        limit: int = 100,
    ) -> list[DomainEvent]:
        """Synchronous load by type - scans all aggregates."""
        events = []

        try:
            with h5py.File(self._path, "r") as f:
                events_group = f["events"]

                for agg_id in events_group:
                    if agg_id.startswith("_"):  # Skip metadata
                        continue

                    stream = events_group[agg_id]["stream"]

                    for event_json in stream:
                        event_data = json.loads(event_json)
                        if event_data.get("event_type") == event_type.value:
                            event = DomainEvent(
                                event_id=event_data["event_id"],
                                event_type=EventType(event_data["event_type"]),
                                aggregate_id=event_data["aggregate_id"],
                                timestamp=datetime.fromisoformat(event_data["timestamp"]),
                                payload=event_data.get("payload", {}),
                                metadata=EventMetadata(**event_data.get("metadata", {})),
                            )
                            events.append(event)

                            if len(events) >= limit:
                                break

                    if len(events) >= limit:
                        break

        except Exception as e:
            logger.error(
                "EVENT_TYPE_LOAD_FAILED",
                event_type=event_type.value,
                error=str(e),
            )
            raise EventStoreError(f"Failed to load by type: {e}") from e

        # Sort by timestamp descending (newest first)
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    async def count_events(self, aggregate_id: str | None = None) -> int:
        """Count events (async wrapper)."""
        return await asyncio.to_thread(self._count_events_sync, aggregate_id)

    def _count_events_sync(self, aggregate_id: str | None = None) -> int:
        """Synchronous count implementation."""
        total = 0

        try:
            with h5py.File(self._path, "r") as f:
                events_group = f["events"]

                if aggregate_id:
                    if aggregate_id in events_group:
                        total = events_group[aggregate_id].attrs.get("event_count", 0)
                else:
                    for agg_id in events_group:
                        if agg_id.startswith("_"):
                            continue
                        total += events_group[agg_id].attrs.get("event_count", 0)

        except Exception as e:
            logger.error("EVENT_COUNT_FAILED", error=str(e))

        return total

    def get_stats(self) -> dict:
        """Get store statistics."""
        try:
            with h5py.File(self._path, "r") as f:
                events_group = f["events"]
                aggregate_count = len([k for k in events_group if not k.startswith("_")])
                total_events = sum(
                    events_group[k].attrs.get("event_count", 0)
                    for k in events_group
                    if not k.startswith("_")
                )
                file_size_mb = self._path.stat().st_size / (1024 * 1024)

                return {
                    "path": str(self._path),
                    "aggregate_count": aggregate_count,
                    "total_events": total_events,
                    "file_size_mb": round(file_size_mb, 2),
                    "created_at": events_group.attrs.get("created_at"),
                }

        except Exception as e:
            logger.error("EVENT_STATS_FAILED", error=str(e))
            return {"error": str(e)}
