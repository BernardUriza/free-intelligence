"""HDF5 Session Repository Implementation.

Author: Claude Code
Created: 2026-01-28
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import h5py

from backend.domain.session import Session, ISessionRepository, SessionMapper, SessionHDF5Metadata
from backend.repositories.interfaces.itask_repository import ITaskRepository


class HDF5SessionRepository(ISessionRepository):
    """Implements ISessionRepository using HDF5 task-based storage (Fix #1).

    Storage-agnostic interface - internal HDF5 structure is an implementation detail.
    Sessions are stored with metadata and associated tasks (transcription, diarization, etc.).
    Structure may change without affecting domain layer.
    """

    def __init__(
        self,
        hdf5_path: str | Path,
        task_repository: ITaskRepository | None = None,
    ):
        """Initialize repository with HDF5 file path.

        Args:
            hdf5_path: Path to HDF5 corpus file
            task_repository: Optional task repository for cascade delete (Fix #5)
        """
        self.hdf5_path = Path(hdf5_path)
        self.task_repository = task_repository
        if not self.hdf5_path.exists():
            raise FileNotFoundError(f"HDF5 file not found: {hdf5_path}")

    def save(self, session: Session) -> str:
        """Persist session entity.

        Args:
            session: Session entity to save

        Returns:
            session_id of persisted session

        Raises:
            ValueError: If session_id already exists
        """
        with h5py.File(self.hdf5_path, "a") as f:
            session_group_path = f"/sessions/{session.session_id}"

            # Check if session already exists
            if session_group_path in f:
                raise ValueError(f"Session {session.session_id} already exists")

            # Create session group
            session_group = f.create_group(session_group_path)

            # Store metadata as JSON attribute (Fix #3 - Type Safety)
            metadata = SessionMapper.to_hdf5_metadata(session)
            session_group.attrs["metadata"] = json.dumps(asdict(metadata))

            # Create subgroups for task-based schema
            session_group.create_group("transcription")
            session_group.create_group("diarization")
            session_group.create_group("soap")
            session_group.create_group("orders")

        return session.session_id

    def find_by_id(self, session_id: str) -> Session | None:
        """Find session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session entity if found, None otherwise
        """
        with h5py.File(self.hdf5_path, "r") as f:
            session_group_path = f"/sessions/{session_id}"

            if session_group_path not in f:
                return None

            session_group = f[session_group_path]
            metadata_json = session_group.attrs.get("metadata")

            if not metadata_json:
                return None

            # Fix #3: Convert dict to typed SessionHDF5Metadata
            metadata_dict = json.loads(metadata_json)
            metadata = SessionHDF5Metadata(**metadata_dict)
            return SessionMapper.from_hdf5(session_id, metadata)

    def find_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        ascending: bool = False
    ) -> list[Session]:
        """Retrieve all sessions with pagination and sorting.

        Args:
            skip: Number of sessions to skip
            limit: Maximum number of sessions to return
            order_by: Field to sort by (created_at, updated_at)
            ascending: Sort order (False = descending, True = ascending)

        Returns:
            List of session entities
        """
        sessions = []

        with h5py.File(self.hdf5_path, "r") as f:
            if "sessions" not in f:
                return []

            sessions_group = f["sessions"]

            # Load all sessions
            for session_id in sessions_group.keys():
                session_group = sessions_group[session_id]
                metadata_json = session_group.attrs.get("metadata")

                if metadata_json:
                    # Fix #3: Convert dict to typed SessionHDF5Metadata
                    metadata_dict = json.loads(metadata_json)
                    metadata = SessionHDF5Metadata(**metadata_dict)
                    session = SessionMapper.from_hdf5(session_id, metadata)
                    sessions.append(session)

        # Sort
        if order_by == "created_at":
            sessions.sort(key=lambda s: s.created_at, reverse=not ascending)
        elif order_by == "updated_at":
            sessions.sort(key=lambda s: s.updated_at, reverse=not ascending)

        # Paginate
        return sessions[skip : skip + limit]

    def update(self, session: Session) -> None:
        """Update existing session.

        Args:
            session: Session entity with updated fields

        Raises:
            ValueError: If session does not exist
        """
        with h5py.File(self.hdf5_path, "a") as f:
            session_group_path = f"/sessions/{session.session_id}"

            if session_group_path not in f:
                raise ValueError(f"Session {session.session_id} not found")

            session_group = f[session_group_path]

            # Update metadata
            metadata = SessionMapper.to_hdf5_metadata(session)
            session_group.attrs["metadata"] = json.dumps(metadata)

    def delete(self, session_id: str) -> bool:
        """Delete session by ID (Fix #5 - with cascade delete).

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if not found

        Side Effects:
            If task_repository is injected, deletes all associated tasks first
            to prevent orphaned task data.
        """
        # CASCADE DELETE: Remove all tasks for this session FIRST
        if self.task_repository is not None:
            deleted_tasks = self.task_repository.delete_by_session(session_id)
            # Note: delete_by_session() logs internally, no need to log here

        with h5py.File(self.hdf5_path, "a") as f:
            session_group_path = f"/sessions/{session_id}"

            if session_group_path not in f:
                return False

            del f[session_group_path]
            return True

    def exists(self, session_id: str) -> bool:
        """Check if session exists.

        Args:
            session_id: Session identifier

        Returns:
            True if session exists, False otherwise
        """
        with h5py.File(self.hdf5_path, "r") as f:
            return f"/sessions/{session_id}" in f

    def count(self) -> int:
        """Count total number of sessions.

        Returns:
            Total session count
        """
        with h5py.File(self.hdf5_path, "r") as f:
            if "sessions" not in f:
                return 0
            return len(f["sessions"].keys())

    def find_by_status(self, status: str) -> list[Session]:
        """Find sessions by status.

        Args:
            status: Session status to filter by

        Returns:
            List of sessions with matching status
        """
        matching_sessions = []

        with h5py.File(self.hdf5_path, "r") as f:
            if "sessions" not in f:
                return []

            sessions_group = f["sessions"]

            for session_id in sessions_group.keys():
                session_group = sessions_group[session_id]
                metadata_json = session_group.attrs.get("metadata")

                if metadata_json:
                    # Fix #3: Convert dict to typed SessionHDF5Metadata
                    metadata_dict = json.loads(metadata_json)
                    if metadata_dict.get("status") == status:
                        metadata = SessionHDF5Metadata(**metadata_dict)
                        session = SessionMapper.from_hdf5(session_id, metadata)
                        matching_sessions.append(session)

        return matching_sessions

    def mark_task_complete(
        self,
        session_id: str,
        task: str,
        completed: bool
    ) -> None:
        """Mark session task as complete/incomplete.

        Args:
            session_id: Session identifier
            task: Task name (transcription, diarization, soap)
            completed: Completion status

        Raises:
            ValueError: If session not found or task invalid
        """
        valid_tasks = ["transcription", "diarization", "soap"]
        if task not in valid_tasks:
            raise ValueError(f"Invalid task: {task}. Must be one of {valid_tasks}")

        session = self.find_by_id(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Update task completion flag
        if task == "transcription":
            session.has_transcription = completed
        elif task == "diarization":
            session.has_diarization = completed
        elif task == "soap":
            session.has_soap = completed

        # Persist update
        self.update(session)

    def find_by_owner(
        self, owner_hash: str, limit: int = 100, offset: int = 0
    ) -> list[Session]:
        """Find sessions by owner.

        Args:
            owner_hash: Owner identifier (hashed user ID)
            limit: Maximum sessions to return
            offset: Number of sessions to skip

        Returns:
            List of Session entities
        """
        matching_sessions = []

        with h5py.File(self.hdf5_path, "r") as f:
            if "sessions" not in f:
                return []

            sessions_group = f["sessions"]

            for session_id in sessions_group.keys():
                session_group = sessions_group[session_id]
                metadata_json = session_group.attrs.get("metadata")

                if metadata_json:
                    metadata_dict = json.loads(metadata_json)
                    if metadata_dict.get("owner_hash") == owner_hash:
                        metadata = SessionHDF5Metadata(**metadata_dict)
                        session = SessionMapper.from_hdf5(session_id, metadata)
                        matching_sessions.append(session)

        # Sort by created_at descending (newest first)
        matching_sessions.sort(key=lambda s: s.created_at, reverse=True)

        # Paginate
        return matching_sessions[offset : offset + limit]

    def count_by_status(self, status: str) -> int:
        """Count sessions by status.

        Args:
            status: Session status to filter (SessionStatus.value or string)

        Returns:
            Count of sessions with given status
        """
        count = 0

        with h5py.File(self.hdf5_path, "r") as f:
            if "sessions" not in f:
                return 0

            sessions_group = f["sessions"]

            for session_id in sessions_group.keys():
                session_group = sessions_group[session_id]
                metadata_json = session_group.attrs.get("metadata")

                if metadata_json:
                    metadata_dict = json.loads(metadata_json)
                    if metadata_dict.get("status") == status:
                        count += 1

        return count
