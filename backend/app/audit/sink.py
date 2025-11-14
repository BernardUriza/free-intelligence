"""Audit sink - Parquet-based event persistence.

Replaces HDF5 audit storage with Parquet partitioned by date.

File: backend/app/audit/sink.py
Card: AUR-PROMPT-3.1
Created: 2025-11-09
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pyarrow as pa
import pyarrow.parquet as pq

from backend.logger import get_logger

logger = get_logger(__name__)

# Read audit root from environment
AUDIT_ROOT = Path(os.getenv("AUDIT_ROOT", "storage/audit"))

# Parquet schema
AUDIT_SCHEMA = pa.schema(
    [
        ("event_id", pa.string()),
        ("timestamp", pa.timestamp("us", tz="UTC")),
        ("action", pa.string()),
        ("user_id", pa.string()),
        ("resource", pa.string()),
        ("result", pa.string()),
        ("metadata", pa.string()),  # JSON-encoded
    ]
)


def write_audit_event(
    action: str,
    user_id: str,
    resource: str,
    result: str,
    metadata: Dict[str, Any] | None = None,
) -> str:
    """Write audit event to Parquet.

    Args:
        action: Action performed (e.g., TIMELINE_HASH_VERIFIED)
        user_id: User/resource identifier
        resource: Resource path
        result: Result status (SUCCESS, FAILED, etc.)
        metadata: Additional context

    Returns:
        event_id (UUID)

    Examples:
        >>> event_id = write_audit_event(
        ...     action="TIMELINE_HASH_VERIFIED",
        ...     user_id="session_20251109_120000",
        ...     resource="/api/timeline/verify-hash",
        ...     result="SUCCESS",
        ...     metadata={"hash": "abc123"}
        ... )
    """
    import json

    event_id = str(uuid.uuid4())
    timestamp = datetime.now(UTC)

    # Partition by date (YYYY-MM-DD)
    partition_date = timestamp.strftime("%Y-%m-%d")
    partition_dir = AUDIT_ROOT / f"date={partition_date}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    # Create record
    record = {
        "event_id": event_id,
        "timestamp": timestamp,
        "action": action,
        "user_id": user_id,
        "resource": resource,
        "result": result,
        "metadata": json.dumps(metadata or {}),
    }

    # Write to Parquet (append mode)
    table = pa.table(
        {
            "event_id": [record["event_id"]],
            "timestamp": [record["timestamp"]],
            "action": [record["action"]],
            "user_id": [record["user_id"]],
            "resource": [record["resource"]],
            "result": [record["result"]],
            "metadata": [record["metadata"]],
        },
        schema=AUDIT_SCHEMA,
    )
    parquet_path = partition_dir / f"events_{uuid.uuid4().hex[:8]}.parquet"

    pq.write_table(table, parquet_path, compression="snappy")

    logger.info(
        "AUDIT_EVENT_WRITTEN",
        event_id=event_id,
        action=action,
        partition=partition_date,
        path=str(parquet_path),
    )

    return event_id


def read_audit_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    action: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Read audit events from Parquet.

    Args:
        start_date: Filter by date >= (YYYY-MM-DD)
        end_date: Filter by date <= (YYYY-MM-DD)
        action: Filter by action

    Returns:
        List of event dicts

    Examples:
        >>> events = read_audit_events(start_date="2025-11-09", action="TIMELINE_HASH_VERIFIED")
    """
    import json

    events = []

    # Scan partitions
    if not AUDIT_ROOT.exists():
        return events

    for partition_dir in sorted(AUDIT_ROOT.glob("date=*")):
        partition_date = partition_dir.name.replace("date=", "")

        # Apply date filters
        if start_date and partition_date < start_date:
            continue
        if end_date and partition_date > end_date:
            continue

        # Read all parquet files in partition
        for parquet_file in partition_dir.glob("*.parquet"):
            table = pq.read_table(parquet_file)

            for row in table.to_pylist():
                # Apply action filter
                if action and row["action"] != action:
                    continue

                # Parse metadata JSON
                row["metadata"] = json.loads(row["metadata"])
                events.append(row)

    return events
