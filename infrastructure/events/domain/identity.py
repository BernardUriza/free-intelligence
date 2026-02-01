"""Event Identity - ULID generation and deduplication.

Uses ULID (Universally Unique Lexicographically Sortable Identifier) for:
- Time-sorted event IDs (no need for separate timestamp index)
- Deduplication via dedupe_key hash
- Exactly-once semantics at EventStore level

ULID format: 01ARZ3NDEKTSV4RRFFQ69G5FAV
- First 10 chars: timestamp (ms precision, sortable)
- Last 16 chars: randomness

Usage:
    from infrastructure.events.domain.identity import generate_event_id, generate_dedupe_key

    event_id = generate_event_id()  # ULID string
    dedupe_key = generate_dedupe_key(EventType.TRANSCRIPTION_STARTED, payload)
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import ulid
from infrastructure.events.domain.events import EventType


def generate_event_id() -> str:
    """Generate a new ULID for event_id.

    Returns:
        ULID string (26 chars, time-sortable)
    """
    return str(ulid.new())


def generate_dedupe_key(
    event_type: EventType,
    aggregate_id: str,
    payload: dict[str, Any],
    key_fields: list[str] | None = None,
) -> str:
    """Generate deduplication key from event type and payload.

    The dedupe_key is a hash that identifies logically identical events.
    Two events with the same dedupe_key are considered duplicates.

    Args:
        event_type: Type of event
        aggregate_id: Aggregate ID (e.g., session_id)
        payload: Event payload
        key_fields: Optional list of payload fields to include in hash.
                   If None, uses all payload fields.

    Returns:
        SHA256 hash (first 16 chars) as dedupe key
    """
    # Build canonical representation
    if key_fields:
        payload_subset = {k: payload.get(k) for k in key_fields if k in payload}
    else:
        payload_subset = payload

    canonical = {
        "type": event_type.value,
        "aggregate": aggregate_id,
        "payload": payload_subset,
    }

    # Serialize deterministically
    json_str = json.dumps(canonical, sort_keys=True, ensure_ascii=False)

    # Hash and truncate
    hash_full = hashlib.sha256(json_str.encode("utf-8")).hexdigest()
    return hash_full[:16]


def extract_timestamp_from_ulid(event_id: str) -> int:
    """Extract Unix timestamp (ms) from ULID.

    Args:
        event_id: ULID string

    Returns:
        Unix timestamp in milliseconds
    """
    try:
        parsed = ulid.parse(event_id)
        return parsed.timestamp().int
    except Exception:
        return 0


def is_ulid(value: str) -> bool:
    """Check if string is valid ULID.

    Args:
        value: String to check

    Returns:
        True if valid ULID
    """
    if not value or len(value) != 26:
        return False
    try:
        ulid.parse(value)
        return True
    except Exception:
        return False


def compare_event_ids(id1: str, id2: str) -> int:
    """Compare two event IDs for ordering.

    Works with both ULID and UUID formats.

    Args:
        id1: First event ID
        id2: Second event ID

    Returns:
        -1 if id1 < id2, 0 if equal, 1 if id1 > id2
    """
    # ULIDs are lexicographically sortable
    if id1 < id2:
        return -1
    elif id1 > id2:
        return 1
    return 0
