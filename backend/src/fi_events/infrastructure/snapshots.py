"""Snapshots - Periodic aggregate state snapshots for fast replay.

Snapshots optimize replay by:
- Storing aggregate state every N events
- Allowing replay from last snapshot instead of beginning
- Including checksum for integrity verification

Storage: Dedicated HDF5 dataset per aggregate

Usage:
    from fi_events.infrastructure.snapshots import SnapshotStore

    store = SnapshotStore()
    await store.save_snapshot("session-123", state, event_version=50)
    snapshot = await store.load_latest("session-123")
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import h5py
from backend.src.fi_common.logging.logger import get_logger
from pathlib import Path

logger = get_logger(__name__)

# Default path for snapshots store
DEFAULT_SNAPSHOTS_PATH = Path("storage/snapshots.h5")

# Snapshot every N events
DEFAULT_SNAPSHOT_INTERVAL = 50


@dataclass
class Snapshot:
    """Aggregate state snapshot."""

    aggregate_id: str
    event_version: int  # Version (event count) at snapshot time
    state: dict[str, Any]
    checksum: str  # SHA256 of serialized state
    created_at: datetime


class SnapshotStore:
    """HDF5-based snapshot storage.

    Layout:
        /snapshots/
            /{aggregate_id}/
                /latest    - Latest snapshot (JSON string)
                /history/  - Historical snapshots (optional)
    """

    def __init__(
        self,
        path: Path | str = DEFAULT_SNAPSHOTS_PATH,
        snapshot_interval: int = DEFAULT_SNAPSHOT_INTERVAL,
    ):
        """Initialize snapshot store.

        Args:
            path: Path to HDF5 file
            snapshot_interval: Create snapshot every N events
        """
        self._path = Path(path)
        self._interval = snapshot_interval

        # Ensure parent directory exists
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize file
        self._initialize_store()

        logger.info(
            "SNAPSHOT_STORE_INITIALIZED",
            path=str(self._path),
            interval=snapshot_interval,
        )

    def _initialize_store(self) -> None:
        """Initialize HDF5 file with root groups."""
        with h5py.File(self._path, "a") as f:
            if "snapshots" not in f:
                f.create_group("snapshots")
                f["snapshots"].attrs["created_at"] = datetime.now(UTC).isoformat()

    def _compute_checksum(self, state: dict[str, Any]) -> str:
        """Compute SHA256 checksum of state.

        Args:
            state: State dict to checksum

        Returns:
            SHA256 hex string
        """
        json_str = json.dumps(state, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    async def save_snapshot(
        self,
        aggregate_id: str,
        state: dict[str, Any],
        event_version: int,
    ) -> Snapshot:
        """Save aggregate snapshot.

        Args:
            aggregate_id: The aggregate ID
            state: Current aggregate state
            event_version: Event count at snapshot time

        Returns:
            The saved Snapshot
        """
        return await asyncio.to_thread(
            self._save_snapshot_sync, aggregate_id, state, event_version
        )

    def _save_snapshot_sync(
        self,
        aggregate_id: str,
        state: dict[str, Any],
        event_version: int,
    ) -> Snapshot:
        """Synchronous save implementation."""
        checksum = self._compute_checksum(state)
        created_at = datetime.now(UTC)

        snapshot_data = {
            "aggregate_id": aggregate_id,
            "event_version": event_version,
            "state": state,
            "checksum": checksum,
            "created_at": created_at.isoformat(),
        }

        with h5py.File(self._path, "a") as f:
            snapshots_group = f["snapshots"]

            # Get or create aggregate group
            if aggregate_id not in snapshots_group:
                snapshots_group.create_group(aggregate_id)

            agg_group = snapshots_group[aggregate_id]

            # Save as "latest"
            if "latest" in agg_group:
                del agg_group["latest"]

            json_str = json.dumps(snapshot_data, ensure_ascii=False)
            dt = h5py.special_dtype(vlen=str)
            agg_group.create_dataset("latest", data=json_str, dtype=dt)

            # Update metadata
            agg_group.attrs["event_version"] = event_version
            agg_group.attrs["updated_at"] = created_at.isoformat()

        logger.info(
            "SNAPSHOT_SAVED",
            aggregate_id=aggregate_id,
            event_version=event_version,
            checksum=checksum[:8],
        )

        return Snapshot(
            aggregate_id=aggregate_id,
            event_version=event_version,
            state=state,
            checksum=checksum,
            created_at=created_at,
        )

    async def load_latest(self, aggregate_id: str) -> Snapshot | None:
        """Load latest snapshot for aggregate.

        Args:
            aggregate_id: The aggregate ID

        Returns:
            Latest Snapshot or None if not found
        """
        return await asyncio.to_thread(self._load_latest_sync, aggregate_id)

    def _load_latest_sync(self, aggregate_id: str) -> Snapshot | None:
        """Synchronous load implementation."""
        try:
            with h5py.File(self._path, "r") as f:
                snapshots_group = f["snapshots"]

                if aggregate_id not in snapshots_group:
                    return None

                agg_group = snapshots_group[aggregate_id]

                if "latest" not in agg_group:
                    return None

                json_str = agg_group["latest"][()]
                if isinstance(json_str, bytes):
                    json_str = json_str.decode("utf-8")

                data = json.loads(json_str)

                return Snapshot(
                    aggregate_id=data["aggregate_id"],
                    event_version=data["event_version"],
                    state=data["state"],
                    checksum=data["checksum"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                )

        except Exception as e:
            logger.error("SNAPSHOT_LOAD_FAILED", aggregate_id=aggregate_id, error=str(e))
            return None

    async def verify_snapshot(self, snapshot: Snapshot) -> bool:
        """Verify snapshot integrity via checksum.

        Args:
            snapshot: Snapshot to verify

        Returns:
            True if checksum matches
        """
        computed = self._compute_checksum(snapshot.state)
        is_valid = computed == snapshot.checksum

        if not is_valid:
            logger.warning(
                "SNAPSHOT_CHECKSUM_MISMATCH",
                aggregate_id=snapshot.aggregate_id,
                expected=snapshot.checksum[:8],
                computed=computed[:8],
            )

        return is_valid

    async def should_snapshot(
        self,
        aggregate_id: str,
        current_event_version: int,
    ) -> bool:
        """Check if snapshot should be created.

        Args:
            aggregate_id: The aggregate ID
            current_event_version: Current event count

        Returns:
            True if snapshot should be created
        """
        latest = await self.load_latest(aggregate_id)

        if latest is None:
            # No snapshot yet - create if we have enough events
            return current_event_version >= self._interval

        events_since_snapshot = current_event_version - latest.event_version
        return events_since_snapshot >= self._interval

    async def delete_snapshot(self, aggregate_id: str) -> bool:
        """Delete snapshot for aggregate.

        Args:
            aggregate_id: The aggregate ID

        Returns:
            True if deleted, False if not found
        """
        return await asyncio.to_thread(self._delete_snapshot_sync, aggregate_id)

    def _delete_snapshot_sync(self, aggregate_id: str) -> bool:
        """Synchronous delete implementation."""
        try:
            with h5py.File(self._path, "a") as f:
                snapshots_group = f["snapshots"]

                if aggregate_id not in snapshots_group:
                    return False

                del snapshots_group[aggregate_id]
                logger.info("SNAPSHOT_DELETED", aggregate_id=aggregate_id)
                return True

        except Exception as e:
            logger.error("SNAPSHOT_DELETE_FAILED", aggregate_id=aggregate_id, error=str(e))
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get snapshot store statistics.

        Returns:
            Stats dict
        """
        try:
            with h5py.File(self._path, "r") as f:
                snapshots_group = f["snapshots"]
                aggregate_count = len(snapshots_group.keys())
                file_size_mb = self._path.stat().st_size / (1024 * 1024)

                return {
                    "path": str(self._path),
                    "aggregate_count": aggregate_count,
                    "file_size_mb": round(file_size_mb, 2),
                    "snapshot_interval": self._interval,
                }

        except Exception as e:
            return {"error": str(e)}


# ============================================================================
# SINGLETON
# ============================================================================

_snapshot_store: SnapshotStore | None = None


def get_snapshot_store() -> SnapshotStore:
    """Get global snapshot store singleton.

    Returns:
        SnapshotStore instance
    """
    global _snapshot_store
    if _snapshot_store is None:
        _snapshot_store = SnapshotStore()
    return _snapshot_store
