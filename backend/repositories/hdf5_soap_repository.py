"""HDF5 SOAP Repository Implementation.

Author: Claude Code
Created: 2026-01-28
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import h5py

from backend.domain.soap import SOAPNote, ISOAPRepository, SOAPMapper, SOAPHDF5Metadata, SOAPHDF5Content


class HDF5SOAPRepository(ISOAPRepository):
    """Implements ISOAPRepository using HDF5 task-based storage.

    Storage structure:
        /sessions/{session_id}/soap/{soap_id}/metadata.json
        /sessions/{session_id}/soap/{soap_id}/content (HDF5 dataset)
    """

    def __init__(self, hdf5_path: str | Path):
        """Initialize repository with HDF5 file path.

        Args:
            hdf5_path: Path to HDF5 corpus file
        """
        self.hdf5_path = Path(hdf5_path)
        if not self.hdf5_path.exists():
            raise FileNotFoundError(f"HDF5 file not found: {hdf5_path}")

    def save(self, soap: SOAPNote) -> str:
        """Persist SOAP note entity.

        Args:
            soap: SOAPNote entity to save

        Returns:
            soap_id of persisted SOAP note

        Raises:
            ValueError: If soap_id already exists
        """
        with h5py.File(self.hdf5_path, "a") as f:
            # Ensure session exists
            session_group_path = f"/sessions/{soap.session_id}"
            if session_group_path not in f:
                raise ValueError(f"Session {soap.session_id} not found")

            # Ensure soap group exists
            soap_group_path = f"{session_group_path}/soap"
            if soap_group_path not in f:
                f.create_group(soap_group_path)

            # Check if SOAP note already exists
            soap_note_group_path = f"{soap_group_path}/{soap.soap_id}"
            if soap_note_group_path in f:
                raise ValueError(f"SOAP note {soap.soap_id} already exists")

            # Create SOAP note group
            soap_note_group = f.create_group(soap_note_group_path)

            # Convert entity to HDF5 format (Fix #3 - Type Safety)
            metadata, content = SOAPMapper.to_hdf5(soap)

            # Store metadata as JSON attribute
            soap_note_group.attrs["metadata"] = json.dumps(asdict(metadata))

            # Store content as JSON (SOAP sections are text, not binary)
            soap_note_group.attrs["content"] = json.dumps(asdict(content))

        return soap.soap_id

    def find_by_id(self, soap_id: str) -> SOAPNote | None:
        """Find SOAP note by ID.

        Args:
            soap_id: SOAP note identifier

        Returns:
            SOAPNote entity if found, None otherwise
        """
        with h5py.File(self.hdf5_path, "r") as f:
            # Search across all sessions
            if "sessions" not in f:
                return None

            for session_id in f["sessions"].keys():
                soap_group_path = f"/sessions/{session_id}/soap"
                if soap_group_path not in f:
                    continue

                soap_note_group_path = f"{soap_group_path}/{soap_id}"
                if soap_note_group_path in f:
                    soap_note_group = f[soap_note_group_path]
                    metadata_json = soap_note_group.attrs.get("metadata")
                    content_json = soap_note_group.attrs.get("content")

                    if metadata_json and content_json:
                        # Fix #3: Convert dicts to typed dataclasses
                        metadata_dict = json.loads(metadata_json)
                        content_dict = json.loads(content_json)
                        metadata = SOAPHDF5Metadata(**metadata_dict)
                        content = SOAPHDF5Content(**content_dict)
                        return SOAPMapper.from_hdf5(soap_id, metadata, content)

            return None

    def find_by_session(self, session_id: str) -> list[SOAPNote]:
        """Find all SOAP notes for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of SOAP notes for the session
        """
        soap_notes = []

        with h5py.File(self.hdf5_path, "r") as f:
            soap_group_path = f"/sessions/{session_id}/soap"

            if soap_group_path not in f:
                return []

            soap_group = f[soap_group_path]

            for soap_id in soap_group.keys():
                soap_note_group = soap_group[soap_id]
                metadata_json = soap_note_group.attrs.get("metadata")
                content_json = soap_note_group.attrs.get("content")

                if metadata_json and content_json:
                    # Fix #3: Convert dicts to typed dataclasses
                    metadata_dict = json.loads(metadata_json)
                    content_dict = json.loads(content_json)
                    metadata = SOAPHDF5Metadata(**metadata_dict)
                    content = SOAPHDF5Content(**content_dict)
                    soap_note = SOAPMapper.from_hdf5(soap_id, metadata, content)
                    soap_notes.append(soap_note)

        return soap_notes

    def find_by_status(self, status: str) -> list[SOAPNote]:
        """Find SOAP notes by status.

        Args:
            status: SOAP note status to filter by

        Returns:
            List of SOAP notes with matching status
        """
        matching_soap_notes = []

        with h5py.File(self.hdf5_path, "r") as f:
            if "sessions" not in f:
                return []

            # Search across all sessions
            for session_id in f["sessions"].keys():
                soap_group_path = f"/sessions/{session_id}/soap"
                if soap_group_path not in f:
                    continue

                soap_group = f[soap_group_path]

                for soap_id in soap_group.keys():
                    soap_note_group = soap_group[soap_id]
                    metadata_json = soap_note_group.attrs.get("metadata")
                    content_json = soap_note_group.attrs.get("content")

                    if metadata_json and content_json:
                        # Fix #3: Convert dicts to typed dataclasses
                        metadata_dict = json.loads(metadata_json)
                        if metadata_dict.get("status") == status:
                            content_dict = json.loads(content_json)
                            metadata = SOAPHDF5Metadata(**metadata_dict)
                            content = SOAPHDF5Content(**content_dict)
                            soap_note = SOAPMapper.from_hdf5(soap_id, metadata, content)
                            matching_soap_notes.append(soap_note)

        return matching_soap_notes

    def update(self, soap: SOAPNote) -> None:
        """Update existing SOAP note.

        Args:
            soap: SOAPNote entity with updated fields

        Raises:
            ValueError: If SOAP note does not exist
        """
        with h5py.File(self.hdf5_path, "a") as f:
            # Search for SOAP note across all sessions
            soap_note_group_path = None

            if "sessions" in f:
                for session_id in f["sessions"].keys():
                    candidate_path = f"/sessions/{session_id}/soap/{soap.soap_id}"
                    if candidate_path in f:
                        soap_note_group_path = candidate_path
                        break

            if not soap_note_group_path:
                raise ValueError(f"SOAP note {soap.soap_id} not found")

            soap_note_group = f[soap_note_group_path]

            # Convert entity to HDF5 format
            metadata, content = SOAPMapper.to_hdf5(soap)

            # Update metadata and content
            soap_note_group.attrs["metadata"] = json.dumps(metadata)
            soap_note_group.attrs["content"] = json.dumps(content)

    def delete(self, soap_id: str) -> bool:
        """Delete SOAP note by ID.

        Args:
            soap_id: SOAP note identifier

        Returns:
            True if SOAP note was deleted, False if not found
        """
        with h5py.File(self.hdf5_path, "a") as f:
            # Search for SOAP note across all sessions
            if "sessions" not in f:
                return False

            for session_id in f["sessions"].keys():
                soap_note_group_path = f"/sessions/{session_id}/soap/{soap_id}"
                if soap_note_group_path in f:
                    del f[soap_note_group_path]
                    return True

            return False

    def exists(self, soap_id: str) -> bool:
        """Check if SOAP note exists.

        Args:
            soap_id: SOAP note identifier

        Returns:
            True if SOAP note exists, False otherwise
        """
        with h5py.File(self.hdf5_path, "r") as f:
            if "sessions" not in f:
                return False

            # Search across all sessions
            for session_id in f["sessions"].keys():
                soap_note_group_path = f"/sessions/{session_id}/soap/{soap_id}"
                if soap_note_group_path in f:
                    return True

            return False

    def count(self, session_id: str | None = None) -> int:
        """Count total number of SOAP notes.

        Args:
            session_id: Optional session ID to count SOAP notes for

        Returns:
            Total SOAP note count (for session if specified, else all)
        """
        with h5py.File(self.hdf5_path, "r") as f:
            if "sessions" not in f:
                return 0

            if session_id:
                # Count SOAP notes for specific session
                soap_group_path = f"/sessions/{session_id}/soap"
                if soap_group_path not in f:
                    return 0
                return len(f[soap_group_path].keys())
            else:
                # Count all SOAP notes across all sessions
                total = 0
                for sess_id in f["sessions"].keys():
                    soap_group_path = f"/sessions/{sess_id}/soap"
                    if soap_group_path in f:
                        total += len(f[soap_group_path].keys())
                return total
