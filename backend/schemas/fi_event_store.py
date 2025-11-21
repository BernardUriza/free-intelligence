from __future__ import annotations

"""
Free Intelligence - Event Store

HDF5-based event store for consultation event streams with SHA256 hashing.

File: backend/fi_event_store.py
Created: 2025-10-28

Architecture:
  /consultations/
    /{consultation_id}/
      /events/              - Event stream (append-only)
      /metadata/            - Consultation metadata
      /snapshots/           - State snapshots (every 50 events)

Event Format:
  - event_id: UUID v4
  - consultation_id: UUID v4
  - timestamp: ISO 8601
  - event_type: str (UPPER_SNAKE_CASE)
  - payload: JSON string
  - audit_hash: SHA256 of payload
  - metadata: JSON string

Usage:
  store = EventStore(corpus_path)
  store.append_event(consultation_id, event)
  events = store.load_stream(consultation_id)
  hash_valid = store.verify_event_hash(event)
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict

import h5py

from backend.logger import get_logger
from backend.providers.models import ConsultationEvent

logger = get_logger(__name__)


# ============================================================================
# SHA256 HASHING
# ============================================================================


def calculate_sha256(data: Dict[str, Any]) -> str:
    """
    Calculate SHA256 hash of data for audit trail.

    Args:
        data: Dictionary to hash

    Returns:
        Hex string of SHA256 hash
    """
    # Serialize to JSON (sorted keys for consistency)
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)

    # Calculate SHA256
    hash_obj = hashlib.sha256(json_str.encode("utf-8"))

    return hash_obj.hexdigest()


def verify_event_hash(event: ConsultationEvent) -> bool:
    """
    Verify event's audit hash matches payload.

    Args:
        event: ConsultationEvent to verify

    Returns:
        True if hash is valid, False otherwise
    """
    if event.audit_hash is None:
        logger.warning("EVENT_HASH_MISSING", event_id=event.event_id, event_type=event.event_type)
        return False

    calculated_hash = calculate_sha256(event.payload)

    is_valid = calculated_hash == event.audit_hash

    if not is_valid:
        logger.error(
            "EVENT_HASH_MISMATCH",
            event_id=event.event_id,
            expected=event.audit_hash,
            calculated=calculated_hash,
        )

    return is_valid


# ============================================================================
# EVENT STORE (HDF5)
# ============================================================================


class EventStore:
    """
    HDF5-based event store for consultation event streams.

    Provides append-only event persistence with SHA256 audit hashing.
    """

    def __init__(self, corpus_path):
        """
        Initialize event store.

        Args:
            corpus_path: Path to HDF5 corpus file
        """
        self.corpus_path = Path(corpus_path)

        if not self.corpus_path.exists():
            raise FileNotFoundError(
                f"Corpus not found: {self.corpus_path}. "
                + "Initialize with corpus_schema.py first."
            )

        logger.info("EVENT_STORE_INITIALIZED", corpus_path=str(self.corpus_path))

    def _ensure_consultation_group(self, h5file: h5py.File, consultation_id: str) -> h5py.Group:
        """
        Ensure consultation group exists in HDF5.

        Args:
            h5file: Open HDF5 file
            consultation_id: Consultation UUID

        Returns:
            Consultation group
        """
        consultations_group = h5file.require_group("/consultations")  # type: ignore[attr-defined]
        consultation_group = consultations_group.require_group(consultation_id)

        # Ensure events dataset exists
        if "events" not in consultation_group:
            # Create expandable dataset for events
            dt = h5py.special_dtype(vlen=str)  # type: ignore[attr-defined]
            consultation_group.create_dataset(
                "events",
                shape=(0,),
                maxshape=(None,),
                dtype=dt,
                compression="gzip",
                compression_opts=4,
            )

        # Ensure metadata attributes
        if "created_at" not in consultation_group.attrs:
            consultation_group.attrs["created_at"] = datetime.now(UTC).isoformat()
            consultation_group.attrs["event_count"] = 0

        return consultation_group

    def append_event(
        self, consultation_id: str, event: ConsultationEvent, calculate_hash: bool = True
    ) -> None:
        """
        Append event to consultation event stream.

        Args:
            consultation_id: Consultation UUID
            event: ConsultationEvent to append
            calculate_hash: Whether to calculate SHA256 hash (default: True)

        Raises:
            ValueError: If event validation fails
        """
        # Calculate audit hash if not present
        if calculate_hash and event.audit_hash is None:
            event.audit_hash = calculate_sha256(event.payload)

        # Serialize event to JSON
        event_json = event.model_dump_json()

        # Append to HDF5
        with h5py.File(self.corpus_path, "a") as h5file:
            # Ensure consultation group
            consultation_group = self._ensure_consultation_group(h5file, consultation_id)

            # Get events dataset
            events_dataset = consultation_group["events"]

            # Resize dataset (append-only)
            current_size = events_dataset.shape[0]  # type: ignore[attr-defined]
            events_dataset.resize((current_size + 1,))  # type: ignore[attr-defined]

            # Write event
            events_dataset[current_size] = event_json  # type: ignore[index]

            # Update metadata
            consultation_group.attrs["event_count"] = current_size + 1
            consultation_group.attrs["updated_at"] = datetime.now(UTC).isoformat()

        logger.info(
            "EVENT_APPENDED",
            consultation_id=consultation_id,
            event_id=event.event_id,
            event_type=event.event_type.value,
            event_count=current_size + 1,
            has_audit_hash=event.audit_hash is not None,
        )

    def load_stream(
        self, consultation_id: str, verify_hashes: bool = False
    ) -> list[ConsultationEvent]:
        """
        Load all events for consultation.

        Args:
            consultation_id: Consultation UUID
            verify_hashes: Whether to verify SHA256 hashes (default: False)

        Returns:
            List of ConsultationEvent in chronological order

        Raises:
            FileNotFoundError: If consultation not found
        """
        with h5py.File(self.corpus_path, "r") as h5file:
            # Check consultation exists
            consultation_path = f"/consultations/{consultation_id}"
            if consultation_path not in h5file:
                raise FileNotFoundError(f"Consultation {consultation_id} not found in event store")

            # Get events dataset
            consultation_group = h5file[consultation_path]
            events_dataset = consultation_group["events"]  # type: ignore[index]

            # Load events
            events = []
            for event_json in events_dataset:  # type: ignore[misc]
                # Deserialize from JSON
                event = ConsultationEvent.model_validate_json(event_json)

                # Verify hash if requested
                if verify_hashes and event.audit_hash:
                    if not verify_event_hash(event):
                        logger.warning("EVENT_HASH_VERIFICATION_FAILED", event_id=event.event_id)

                events.append(event)

        logger.info(
            "STREAM_LOADED",
            consultation_id=consultation_id,
            event_count=len(events),
            hashes_verified=verify_hashes,
        )

        return events

    def get_consultation_metadata(self, consultation_id: str) -> dict[str, Any]:
        """
        Get consultation metadata.

        Args:
            consultation_id: Consultation UUID

        Returns:
            Dictionary with metadata

        Raises:
            FileNotFoundError: If consultation not found
        """
        with h5py.File(self.corpus_path, "r") as h5file:
            consultation_path = f"/consultations/{consultation_id}"
            if consultation_path not in h5file:
                raise FileNotFoundError(f"Consultation {consultation_id} not found")

            consultation_group = h5file[consultation_path]

            return {
                "consultation_id": consultation_id,
                "created_at": consultation_group.attrs.get("created_at"),  # type: ignore[attr-defined]
                "updated_at": consultation_group.attrs.get("updated_at"),  # type: ignore[attr-defined]
                "event_count": consultation_group.attrs.get("event_count", 0),  # type: ignore[attr-defined]
            }

    def get_event_count(self, consultation_id: str) -> int:
        """
        Get event count for consultation.

        Args:
            consultation_id: Consultation UUID

        Returns:
            Number of events

        Raises:
            FileNotFoundError: If consultation not found
        """
        metadata = self.get_consultation_metadata(consultation_id)
        return metadata["event_count"]

    def consultation_exists(self, consultation_id: str) -> bool:
        """
        Check if consultation exists.

        Args:
            consultation_id: Consultation UUID

        Returns:
            True if exists, False otherwise
        """
        with h5py.File(self.corpus_path, "r") as h5file:
            consultation_path = f"/consultations/{consultation_id}"
            return consultation_path in h5file

    def list_consultations(self) -> list[dict[str, Any]]:
        """
        List all consultations in store.

        Returns:
            List of consultation metadata dictionaries
        """
        consultations = []

        with h5py.File(self.corpus_path, "r") as h5file:
            if "/consultations" not in h5file:
                return []

            consultations_group = h5file["/consultations"]

            for consultation_id in consultations_group.keys():  # type: ignore[attr-defined]
                try:
                    metadata = self.get_consultation_metadata(consultation_id)
                    consultations.append(metadata)
                except Exception as e:
                    logger.warning(
                        "CONSULTATION_METADATA_ERROR", consultation_id=consultation_id, error=str(e)
                    )

        return consultations

    def create_snapshot(self, consultation_id: str, state: Dict[str, Any]) -> None:
        """
        Create state snapshot for performance optimization.

        Snapshots allow faster state reconstruction by avoiding full replay.

        Args:
            consultation_id: Consultation UUID
            state: Current consultation state
        """
        with h5py.File(self.corpus_path, "a") as h5file:
            consultation_path = f"/consultations/{consultation_id}"
            if consultation_path not in h5file:
                raise FileNotFoundError(f"Consultation {consultation_id} not found")

            consultation_group = h5file[consultation_path]

            # Ensure snapshots group
            snapshots_group = consultation_group.require_group("snapshots")  # type: ignore[attr-defined]

            # Create snapshot dataset
            snapshot_name = datetime.now(UTC).isoformat()
            snapshot_json = json.dumps(state)

            dt = h5py.special_dtype(vlen=str)  # type: ignore[attr-defined]
            snapshot_dataset = snapshots_group.create_dataset(
                snapshot_name, data=snapshot_json, dtype=dt
            )

            # Store metadata
            snapshot_dataset.attrs["event_count"] = self.get_event_count(consultation_id)
            snapshot_dataset.attrs["created_at"] = snapshot_name

        logger.info(
            "SNAPSHOT_CREATED",
            consultation_id=consultation_id,
            snapshot_name=snapshot_name,
            event_count=snapshot_dataset.attrs["event_count"],
        )

    def get_latest_snapshot(self, consultation_id: str) -> dict[str, Any | None] | None:
        """
        Get latest snapshot for consultation.

        Args:
            consultation_id: Consultation UUID

        Returns:
            Snapshot state dict or None if no snapshots
        """
        with h5py.File(self.corpus_path, "r") as h5file:
            consultation_path = f"/consultations/{consultation_id}/snapshots"
            if consultation_path not in h5file:
                return None

            snapshots_group = h5file[consultation_path]

            if len(snapshots_group.keys()) == 0:  # type: ignore[attr-defined]
                return None

            # Get latest snapshot (sorted by name = ISO timestamp)
            snapshot_names = sorted(snapshots_group.keys())  # type: ignore[attr-defined]
            latest_name = snapshot_names[-1]

            snapshot_dataset = snapshots_group[latest_name]  # type: ignore[index]
            snapshot_json = snapshot_dataset[()]  # type: ignore[index]

            return json.loads(snapshot_json)

    def get_stats(self) -> dict[str, Any]:
        """
        Get event store statistics.

        Returns:
            Dictionary with statistics
        """
        with h5py.File(self.corpus_path, "r") as h5file:
            if "/consultations" not in h5file:
                return {"total_consultations": 0, "total_events": 0, "file_size_mb": 0}

            consultations_group = h5file["/consultations"]
            consultation_count = len(consultations_group.keys())  # type: ignore[attr-defined]

            total_events = 0
            for consultation_id in consultations_group.keys():  # type: ignore[attr-defined]
                try:
                    metadata = self.get_consultation_metadata(consultation_id)
                    total_events += metadata["event_count"]
                except (KeyError, ValueError, AttributeError) as e:
                    logger.debug(
                        "CONSULTATION_METADATA_FAILED",
                        consultation_id=consultation_id,
                        error=str(e),
                    )

            file_size_mb = self.corpus_path.stat().st_size / (1024 * 1024)

        return {
            "total_consultations": consultation_count,
            "total_events": total_events,
            "file_size_mb": round(file_size_mb, 2),
            "corpus_path": str(self.corpus_path),
        }


# ============================================================================
# CLI INTERFACE
# ============================================================================


def main():
    """CLI interface for event store."""
    import argparse

    parser = argparse.ArgumentParser(description="Free Intelligence Event Store CLI")
    parser.add_argument("--corpus", default="storage/corpus.h5", help="Path to HDF5 corpus file")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # List command
    _list_parser = subparsers.add_parser("list", help="List consultations")

    # Load command
    load_parser = subparsers.add_parser("load", help="Load event stream")
    load_parser.add_argument("consultation_id", help="Consultation UUID")
    load_parser.add_argument("--verify", action="store_true", help="Verify SHA256 hashes")

    # Stats command
    _stats_parser = subparsers.add_parser("stats", help="Show statistics")

    args = parser.parse_args()

    # Initialize event store
    store = EventStore(args.corpus)

    # Execute command
    if args.command == "list":
        consultations = store.list_consultations()
        print(f"\nTotal consultations: {len(consultations)}\n")
        for c in consultations:
            print(f"  {c['consultation_id']}")
            print(f"    Events: {c['event_count']}")
            print(f"    Created: {c['created_at']}")
            print(f"    Updated: {c.get('updated_at', 'N/A')}")
            print()

    elif args.command == "load":
        events = store.load_stream(args.consultation_id, verify_hashes=args.verify)
        print(f"\nLoaded {len(events)} events\n")
        for i, event in enumerate(events, 1):
            print(f"  [{i}] {event.event_type.value}")
            print(f"      ID: {event.event_id}")
            print(f"      Time: {event.timestamp}")
            print(
                f"      Hash: {event.audit_hash[:16]}..."
                if event.audit_hash
                else "      Hash: None"
            )
            print()

    elif args.command == "stats":
        stats = store.get_stats()
        print("\nEvent Store Statistics")
        print("=" * 50)
        print(f"  Corpus: {stats['corpus_path']}")
        print(f"  Total consultations: {stats['total_consultations']}")
        print(f"  Total events: {stats['total_events']}")
        print(f"  File size: {stats['file_size_mb']} MB")
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
