"""Consumer Offsets - Track consumer positions in event stream.

Consumer offsets enable:
- Exactly-once processing (at-least-once + idempotency)
- Resume from last position after restart
- Lag monitoring (current position vs head)
- Consumer group coordination

Storage: HDF5 dataset per consumer group

Usage:
    from fi_events.infrastructure.consumer_offsets import (
        ConsumerOffsetStore,
        get_offset_store,
    )

    store = get_offset_store()
    await store.commit("my-consumer", "session-123", "01ARZ3NDEK...")
    position = await store.get_position("my-consumer", "session-123")
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import h5py
from backend.src.fi_common.logging.logger import get_logger
from pathlib import Path

logger = get_logger(__name__)

# Default path for consumer offsets
DEFAULT_OFFSETS_PATH = Path("storage/consumer_offsets.h5")


@dataclass
class ConsumerPosition:
    """Position of a consumer in an event stream."""

    consumer_group: str
    aggregate_id: str  # Which stream (e.g., session_id or "__global__")
    last_event_id: str
    last_event_timestamp: datetime
    committed_at: datetime
    events_processed: int


@dataclass
class ConsumerLag:
    """Lag information for a consumer."""

    consumer_group: str
    aggregate_id: str
    current_position: str | None  # Last processed event_id
    head_position: str | None  # Latest event_id in stream
    lag_events: int  # Number of events behind
    lag_ms: float  # Time behind in milliseconds


class ConsumerOffsetStore:
    """HDF5-based consumer offset storage.

    Layout:
        /offsets/
            /{consumer_group}/
                /{aggregate_id} -> JSON with position data
    """

    def __init__(self, path: Path | str = DEFAULT_OFFSETS_PATH):
        """Initialize offset store.

        Args:
            path: Path to HDF5 file
        """
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_store()

        logger.info("CONSUMER_OFFSET_STORE_INITIALIZED", path=str(self._path))

    def _initialize_store(self) -> None:
        """Initialize HDF5 file structure."""
        with h5py.File(self._path, "a") as f:
            if "offsets" not in f:
                f.create_group("offsets")
                f["offsets"].attrs["created_at"] = datetime.now(UTC).isoformat()

    async def commit(
        self,
        consumer_group: str,
        aggregate_id: str,
        event_id: str,
        event_timestamp: datetime | None = None,
        events_processed: int = 1,
    ) -> ConsumerPosition:
        """Commit consumer position.

        Args:
            consumer_group: Consumer group name
            aggregate_id: Stream identifier (session_id or "__global__")
            event_id: Last processed event_id
            event_timestamp: Timestamp of last event
            events_processed: Total events processed

        Returns:
            Updated ConsumerPosition
        """
        return await asyncio.to_thread(
            self._commit_sync,
            consumer_group,
            aggregate_id,
            event_id,
            event_timestamp or datetime.now(UTC),
            events_processed,
        )

    def _commit_sync(
        self,
        consumer_group: str,
        aggregate_id: str,
        event_id: str,
        event_timestamp: datetime,
        events_processed: int,
    ) -> ConsumerPosition:
        """Synchronous commit implementation."""
        committed_at = datetime.now(UTC)

        position_data = {
            "consumer_group": consumer_group,
            "aggregate_id": aggregate_id,
            "last_event_id": event_id,
            "last_event_timestamp": event_timestamp.isoformat(),
            "committed_at": committed_at.isoformat(),
            "events_processed": events_processed,
        }

        with h5py.File(self._path, "a") as f:
            offsets_group = f["offsets"]

            # Get or create consumer group
            if consumer_group not in offsets_group:
                offsets_group.create_group(consumer_group)

            group = offsets_group[consumer_group]

            # Save position
            safe_agg_id = self._safe_key(aggregate_id)
            if safe_agg_id in group:
                del group[safe_agg_id]

            json_str = json.dumps(position_data, ensure_ascii=False)
            dt = h5py.special_dtype(vlen=str)
            group.create_dataset(safe_agg_id, data=json_str, dtype=dt)

        logger.debug(
            "OFFSET_COMMITTED",
            consumer_group=consumer_group,
            aggregate_id=aggregate_id,
            event_id=event_id[:16],
        )

        return ConsumerPosition(
            consumer_group=consumer_group,
            aggregate_id=aggregate_id,
            last_event_id=event_id,
            last_event_timestamp=event_timestamp,
            committed_at=committed_at,
            events_processed=events_processed,
        )

    async def get_position(
        self,
        consumer_group: str,
        aggregate_id: str,
    ) -> ConsumerPosition | None:
        """Get consumer position.

        Args:
            consumer_group: Consumer group name
            aggregate_id: Stream identifier

        Returns:
            ConsumerPosition or None if not found
        """
        return await asyncio.to_thread(
            self._get_position_sync,
            consumer_group,
            aggregate_id,
        )

    def _get_position_sync(
        self,
        consumer_group: str,
        aggregate_id: str,
    ) -> ConsumerPosition | None:
        """Synchronous get position implementation."""
        try:
            with h5py.File(self._path, "r") as f:
                offsets_group = f["offsets"]

                if consumer_group not in offsets_group:
                    return None

                group = offsets_group[consumer_group]
                safe_agg_id = self._safe_key(aggregate_id)

                if safe_agg_id not in group:
                    return None

                json_str = group[safe_agg_id][()]
                if isinstance(json_str, bytes):
                    json_str = json_str.decode("utf-8")

                data = json.loads(json_str)

                return ConsumerPosition(
                    consumer_group=data["consumer_group"],
                    aggregate_id=data["aggregate_id"],
                    last_event_id=data["last_event_id"],
                    last_event_timestamp=datetime.fromisoformat(data["last_event_timestamp"]),
                    committed_at=datetime.fromisoformat(data["committed_at"]),
                    events_processed=data.get("events_processed", 0),
                )

        except Exception as e:
            logger.error(
                "OFFSET_LOAD_FAILED",
                consumer_group=consumer_group,
                aggregate_id=aggregate_id,
                error=str(e),
            )
            return None

    async def get_lag(
        self,
        consumer_group: str,
        aggregate_id: str,
        head_event_id: str | None,
        head_event_timestamp: datetime | None,
        total_events: int,
    ) -> ConsumerLag:
        """Calculate consumer lag.

        Args:
            consumer_group: Consumer group name
            aggregate_id: Stream identifier
            head_event_id: Latest event_id in stream
            head_event_timestamp: Timestamp of latest event
            total_events: Total events in stream

        Returns:
            ConsumerLag with lag metrics
        """
        position = await self.get_position(consumer_group, aggregate_id)

        if position is None:
            return ConsumerLag(
                consumer_group=consumer_group,
                aggregate_id=aggregate_id,
                current_position=None,
                head_position=head_event_id,
                lag_events=total_events,
                lag_ms=0.0,
            )

        lag_events = total_events - position.events_processed
        lag_ms = 0.0

        if head_event_timestamp and position.last_event_timestamp:
            delta = head_event_timestamp - position.last_event_timestamp
            lag_ms = delta.total_seconds() * 1000

        return ConsumerLag(
            consumer_group=consumer_group,
            aggregate_id=aggregate_id,
            current_position=position.last_event_id,
            head_position=head_event_id,
            lag_events=max(0, lag_events),
            lag_ms=max(0.0, lag_ms),
        )

    async def list_consumers(self) -> list[str]:
        """List all consumer groups.

        Returns:
            List of consumer group names
        """
        return await asyncio.to_thread(self._list_consumers_sync)

    def _list_consumers_sync(self) -> list[str]:
        """Synchronous list consumers implementation."""
        try:
            with h5py.File(self._path, "r") as f:
                offsets_group = f["offsets"]
                return list(offsets_group.keys())
        except Exception:
            return []

    async def list_positions(
        self,
        consumer_group: str,
    ) -> list[ConsumerPosition]:
        """List all positions for a consumer group.

        Args:
            consumer_group: Consumer group name

        Returns:
            List of ConsumerPosition
        """
        return await asyncio.to_thread(self._list_positions_sync, consumer_group)

    def _list_positions_sync(self, consumer_group: str) -> list[ConsumerPosition]:
        """Synchronous list positions implementation."""
        positions = []
        try:
            with h5py.File(self._path, "r") as f:
                offsets_group = f["offsets"]

                if consumer_group not in offsets_group:
                    return []

                group = offsets_group[consumer_group]

                for key in group.keys():
                    json_str = group[key][()]
                    if isinstance(json_str, bytes):
                        json_str = json_str.decode("utf-8")

                    data = json.loads(json_str)
                    positions.append(
                        ConsumerPosition(
                            consumer_group=data["consumer_group"],
                            aggregate_id=data["aggregate_id"],
                            last_event_id=data["last_event_id"],
                            last_event_timestamp=datetime.fromisoformat(
                                data["last_event_timestamp"]
                            ),
                            committed_at=datetime.fromisoformat(data["committed_at"]),
                            events_processed=data.get("events_processed", 0),
                        )
                    )

        except Exception as e:
            logger.error("OFFSET_LIST_FAILED", consumer_group=consumer_group, error=str(e))

        return positions

    async def reset_consumer(self, consumer_group: str) -> bool:
        """Reset all positions for a consumer group.

        Args:
            consumer_group: Consumer group to reset

        Returns:
            True if reset, False if not found
        """
        return await asyncio.to_thread(self._reset_consumer_sync, consumer_group)

    def _reset_consumer_sync(self, consumer_group: str) -> bool:
        """Synchronous reset consumer implementation."""
        try:
            with h5py.File(self._path, "a") as f:
                offsets_group = f["offsets"]

                if consumer_group not in offsets_group:
                    return False

                del offsets_group[consumer_group]
                logger.info("CONSUMER_RESET", consumer_group=consumer_group)
                return True

        except Exception as e:
            logger.error("CONSUMER_RESET_FAILED", consumer_group=consumer_group, error=str(e))
            return False

    def _safe_key(self, key: str) -> str:
        """Make key safe for HDF5 (no slashes).

        Args:
            key: Original key

        Returns:
            Safe key for HDF5
        """
        return key.replace("/", "_").replace("\\", "_")

    def get_stats(self) -> dict[str, Any]:
        """Get offset store statistics.

        Returns:
            Stats dict
        """
        try:
            with h5py.File(self._path, "r") as f:
                offsets_group = f["offsets"]
                consumer_count = len(offsets_group.keys())

                total_positions = 0
                for group_name in offsets_group.keys():
                    total_positions += len(offsets_group[group_name].keys())

                file_size_kb = self._path.stat().st_size / 1024

                return {
                    "path": str(self._path),
                    "consumer_groups": consumer_count,
                    "total_positions": total_positions,
                    "file_size_kb": round(file_size_kb, 2),
                }

        except Exception as e:
            return {"error": str(e)}


# ============================================================================
# SINGLETON
# ============================================================================

_offset_store: ConsumerOffsetStore | None = None


def get_offset_store() -> ConsumerOffsetStore:
    """Get global consumer offset store singleton.

    Returns:
        ConsumerOffsetStore instance
    """
    global _offset_store
    if _offset_store is None:
        _offset_store = ConsumerOffsetStore()
    return _offset_store


def reset_offset_store() -> None:
    """Reset the global offset store (for testing)."""
    global _offset_store
    _offset_store = None
