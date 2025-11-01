#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Sessions Store

JSONL-based session storage with file locking for atomicity.

File: backend/sessions_store.py
Card: FI-API-FEAT-009
Created: 2025-10-29

Storage format:
- data/sessions/manifest.jsonl (1 line per session, append-only)
- data/sessions/index.json (id -> file offset mapping for fast lookups)

Session schema:
{
    "id": "01JBEXAMPLE123",  # ULID
    "created_at": "2025-10-29T21:30:00Z",
    "updated_at": "2025-10-29T21:35:00Z",
    "last_active": "2025-10-29T21:35:00Z",
    "interaction_count": 5,
    "status": "active",  # new|active|complete
    "is_persisted": true,
    "owner_hash": "sha256:abc...",
    "thread_id": "thread_xyz"  # nullable
}
"""

import fcntl
import json
import os
import random

# ULID generation (simple implementation)
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional


def generate_ulid() -> str:
    """Generate ULID (millisecond timestamp + randomness)"""
    timestamp = int(time.time() * 1000)
    randomness = random.randint(0, 2**80 - 1)
    return f"{timestamp:013x}{randomness:020x}".upper()


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class Session:
    """Session data model"""

    id: str
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601
    last_active: str  # ISO 8601
    interaction_count: int
    status: str  # new|active|complete
    is_persisted: bool
    owner_hash: str
    thread_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> Session:
        """Create from dictionary"""
        return Session(**data)


# ============================================================================
# SESSIONS STORE
# ============================================================================


class SessionsStore:
    """
    JSONL-based sessions storage with atomic operations.

    Storage:
    - manifest.jsonl: append-only log of all sessions
    - index.json: id -> line offset mapping for O(1) lookups
    """

    def __init__(self, data_dir: str = "data/sessions"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.data_dir / "manifest.jsonl"
        self.index_path = self.data_dir / "index.json"

        # Initialize files if they don't exist
        if not self.manifest_path.exists():
            self.manifest_path.touch()
        if not self.index_path.exists():
            self._write_index({})

    def _read_index(self) -> dict[str, int]:
        """Read index with file lock"""
        if not self.index_path.exists():
            return {}

        with open(self.index_path) as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                data = json.load(f)
                return data
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _write_index(self, index: dict[str, int]):
        """Write index with file lock"""
        with open(self.index_path, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(index, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def create(
        self,
        owner_hash: str,
        status: str = "new",
        thread_id: Optional[str] = None,
    ) -> Session:
        """
        Create new session atomically.

        Args:
            owner_hash: SHA256 hash of owner
            status: Initial status (default: "new")
            thread_id: Optional thread identifier

        Returns:
            Created Session instance
        """
        now = datetime.now(UTC).isoformat() + "Z"
        session = Session(
            id=generate_ulid(),
            created_at=now,
            updated_at=now,
            last_active=now,
            interaction_count=0,
            status=status,
            is_persisted=True,
            owner_hash=owner_hash,
            thread_id=thread_id,
        )

        # Append to manifest with lock
        with open(self.manifest_path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                offset = f.tell()
                json.dump(session.to_dict(), f)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())

                # Update index
                index = self._read_index()
                index[session.id] = offset
                self._write_index(index)

            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        return session

    def get(self, session_id: str) -> Optional[Session]:
        """
        Get session by ID.

        Args:
            session_id: Session ID (ULID)

        Returns:
            Session instance or None if not found
        """
        index = self._read_index()
        offset = index.get(session_id)

        if offset is None:
            return None

        with open(self.manifest_path) as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                f.seek(offset)
                line = f.readline().strip()
                if not line:
                    return None
                data = json.loads(line)
                return Session.from_dict(data)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        owner_hash: Optional[str] = None,
    ) -> list[Session]:
        """
        List sessions with pagination.

        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            owner_hash: Optional filter by owner_hash

        Returns:
            List of Session instances (deduplicated, latest version per ID)
        """
        sessions_by_id: dict[str, Session] = {}

        with open(self.manifest_path) as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                # Read all lines and keep latest version per ID
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    session = Session.from_dict(data)

                    # Filter by owner_hash if provided
                    if owner_hash and session.owner_hash != owner_hash:
                        continue

                    # Keep latest version (append-only: later lines override)
                    sessions_by_id[session.id] = session
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # Convert to list and sort by created_at descending (newest first)
        sessions = list(sessions_by_id.values())
        sessions.sort(key=lambda s: s.created_at, reverse=True)

        # Apply pagination
        return sessions[offset : offset + limit]

    def update(
        self,
        session_id: str,
        status: Optional[str] = None,
        last_active: Optional[str] = None,
        interaction_count: Optional[int] = None,
    ) -> Optional[Session]:
        """
        Update session (append-only: creates new entry).

        Args:
            session_id: Session ID to update
            status: New status (if provided)
            last_active: New last_active timestamp (if provided)
            interaction_count: New interaction count (if provided)

        Returns:
            Updated Session or None if not found
        """
        # Get current session
        current = self.get(session_id)
        if not current:
            return None

        # Create updated session
        now = datetime.now(UTC).isoformat() + "Z"
        updated = Session(
            id=current.id,
            created_at=current.created_at,
            updated_at=now,
            last_active=last_active if last_active else current.last_active,
            interaction_count=(
                interaction_count if interaction_count is not None else current.interaction_count
            ),
            status=status if status else current.status,
            is_persisted=True,
            owner_hash=current.owner_hash,
            thread_id=current.thread_id,
        )

        # Append to manifest (new entry)
        with open(self.manifest_path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                offset = f.tell()
                json.dump(updated.to_dict(), f)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())

                # Update index to point to new offset
                index = self._read_index()
                index[session_id] = offset
                self._write_index(index)

            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        return updated

    def count(self, owner_hash: Optional[str] = None) -> int:
        """
        Count total sessions.

        Args:
            owner_hash: Optional filter by owner_hash

        Returns:
            Total count of sessions
        """
        count = 0

        with open(self.manifest_path) as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if owner_hash:
                        data = json.loads(line)
                        if data.get("owner_hash") == owner_hash:
                            count += 1
                    else:
                        count += 1
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # Subtract duplicates (updates create new entries)
        # Use index to get unique count
        index = self._read_index()
        if owner_hash:
            # Need to count owner_hash in unique sessions
            unique_sessions = set()
            for session_id in index.keys():
                session = self.get(session_id)
                if session and session.owner_hash == owner_hash:
                    unique_sessions.add(session_id)
            return len(unique_sessions)
        else:
            return len(index)
