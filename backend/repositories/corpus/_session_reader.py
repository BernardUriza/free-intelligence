"""Session read/write operations for the corpus HDF5 store.

Provides metadata retrieval, metadata updates, audio access,
transcription-chunk reads, workflow state, generic dataset access,
and task listing — all scoped to a single session.

Author: Bernard Uriza Orozco
"""

from __future__ import annotations

import json
from typing import Any

import h5py
import numpy as np
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)

# HDF5 top-level group where sessions live.
SESSIONS_GROUP = "sessions"


class SessionReader:
    """Read and mutate individual session data inside HDF5.

    Every method operates on a single ``session_id`` beneath the
    ``sessions/`` HDF5 group.  Write operations follow the
    append-only pattern where possible (metadata merge rather than
    wholesale overwrite).
    """

    def __init__(
        self,
        open_file: Any,
        log_operation: Any,
    ) -> None:
        self._open_file = open_file
        self._log_operation = log_operation

    # -- metadata ------------------------------------------------------------

    def get_session_metadata(self, session_id: str) -> dict[str, Any] | None:
        """Return merged attrs + ``meta`` dataset for *session_id*."""
        try:
            with self._open_file("r") as f:
                session_path = f"{SESSIONS_GROUP}/{session_id}"
                if session_path not in f:
                    return None

                session_group = f[session_path]
                metadata: dict[str, Any] = dict(session_group.attrs)

                if "meta" in session_group:
                    meta_ds = session_group["meta"]
                    if isinstance(meta_ds, h5py.Dataset):
                        meta_bytes = bytes(meta_ds[()])
                        meta_json = json.loads(meta_bytes.decode("utf-8"))
                        metadata.update(meta_json)

                logger.debug("SESSION_METADATA_READ", session_id=session_id)
                return metadata

        except Exception as e:
            logger.error(
                "GET_SESSION_METADATA_FAILED",
                session_id=session_id,
                error=str(e),
            )
            return None

    def update_session_metadata(
        self, session_id: str, updates: dict[str, Any]
    ) -> bool:
        """Merge *updates* into the session's ``meta`` dataset.

        Existing keys are preserved unless overridden by *updates*.
        The old ``meta`` dataset is deleted and recreated (HDF5
        limitation) but no historical data is lost because callers
        always merge.

        Returns:
            ``True`` on success, ``False`` if the session is missing.
        """
        try:
            with self._open_file("a") as f:
                session_path = f"{SESSIONS_GROUP}/{session_id}"
                if session_path not in f:
                    logger.warning(
                        "SESSION_NOT_FOUND_FOR_UPDATE", session_id=session_id
                    )
                    return False

                session_group = f[session_path]

                # Read existing meta (if any) then merge
                existing_meta: dict[str, Any] = {}
                if "meta" in session_group:
                    meta_ds = session_group["meta"]
                    if isinstance(meta_ds, h5py.Dataset):
                        meta_bytes = bytes(meta_ds[()])
                        existing_meta = json.loads(meta_bytes.decode("utf-8"))
                    del session_group["meta"]

                existing_meta.update(updates)

                meta_bytes = json.dumps(existing_meta).encode("utf-8")
                session_group.create_dataset(
                    "meta",
                    data=np.frombuffer(meta_bytes, dtype=np.uint8),
                    compression="gzip",
                )

                logger.info(
                    "SESSION_METADATA_UPDATED",
                    session_id=session_id,
                    updated_keys=list(updates.keys()),
                )
                return True

        except Exception as e:
            logger.error(
                "UPDATE_SESSION_METADATA_FAILED",
                session_id=session_id,
                error=str(e),
            )
            return False

    # -- audio ---------------------------------------------------------------

    def get_session_audio(
        self,
        session_id: str,
        audio_type: str = "full_audio.webm",
    ) -> bytes | None:
        """Return raw audio bytes for the given *audio_type* dataset."""
        try:
            with self._open_file("r") as f:
                audio_path = f"{SESSIONS_GROUP}/{session_id}/{audio_type}"
                if audio_path not in f:
                    return None

                audio_bytes = bytes(f[audio_path][()])

                logger.debug(
                    "SESSION_AUDIO_READ",
                    session_id=session_id,
                    audio_type=audio_type,
                    size_bytes=len(audio_bytes),
                )
                return audio_bytes

        except Exception as e:
            logger.error(
                "GET_SESSION_AUDIO_FAILED",
                session_id=session_id,
                audio_type=audio_type,
                error=str(e),
            )
            return None

    # -- transcription chunks ------------------------------------------------

    def get_session_transcription_chunks(
        self,
        session_id: str,
        task_type: str = "TRANSCRIPTION",
    ) -> list[dict[str, Any]]:
        """Return ordered chunks (attrs + transcript text) for a task."""
        try:
            with self._open_file("r") as f:
                chunks_path = (
                    f"{SESSIONS_GROUP}/{session_id}/tasks/{task_type}/chunks"
                )
                if chunks_path not in f:
                    return []

                chunks_group = f[chunks_path]
                chunks: list[dict[str, Any]] = []

                for chunk_name in chunks_group.keys():
                    chunk_group = chunks_group[chunk_name]
                    chunk_data: dict[str, Any] = {"chunk_name": chunk_name}

                    for key, value in chunk_group.attrs.items():
                        chunk_data[key] = value

                    if "transcript" in chunk_group:
                        transcript_ds = chunk_group["transcript"]
                        if isinstance(transcript_ds, h5py.Dataset):
                            raw = bytes(transcript_ds[()])
                            chunk_data["transcript"] = raw.decode("utf-8")

                    chunks.append(chunk_data)

                logger.debug(
                    "SESSION_CHUNKS_READ",
                    session_id=session_id,
                    task_type=task_type,
                    chunk_count=len(chunks),
                )
                return chunks

        except Exception as e:
            logger.error(
                "GET_SESSION_CHUNKS_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e),
            )
            return []

    # -- workflow state ------------------------------------------------------

    def get_session_workflow_state(
        self, session_id: str
    ) -> dict[str, Any] | None:
        """Return the session's workflow state (attrs + ``state`` dataset)."""
        try:
            with self._open_file("r") as f:
                workflow_path = f"{SESSIONS_GROUP}/{session_id}/workflow"
                if workflow_path not in f:
                    return None

                workflow_group = f[workflow_path]
                workflow_state: dict[str, Any] = dict(workflow_group.attrs)

                if "state" in workflow_group:
                    state_ds = workflow_group["state"]
                    if isinstance(state_ds, h5py.Dataset):
                        state_bytes = bytes(state_ds[()])
                        state_json = json.loads(state_bytes.decode("utf-8"))
                        workflow_state.update(state_json)

                logger.debug("WORKFLOW_STATE_READ", session_id=session_id)
                return workflow_state

        except Exception as e:
            logger.error(
                "GET_WORKFLOW_STATE_FAILED",
                session_id=session_id,
                error=str(e),
            )
            return None

    # -- generic dataset access ----------------------------------------------

    def get_session_dataset(
        self, session_id: str, dataset_path: str
    ) -> bytes | None:
        """Return raw bytes from an arbitrary dataset below the session.

        Args:
            session_id: Session identifier.
            dataset_path: Relative path inside the session group
                (e.g. ``"tasks/TRANSCRIPTION/webspeech_final"``).
        """
        try:
            with self._open_file("r") as f:
                full_path = f"{SESSIONS_GROUP}/{session_id}/{dataset_path}"
                if full_path not in f:
                    return None

                dataset_bytes = bytes(f[full_path][()])

                logger.debug(
                    "SESSION_DATASET_READ",
                    session_id=session_id,
                    dataset_path=dataset_path,
                    size_bytes=len(dataset_bytes),
                )
                return dataset_bytes

        except Exception as e:
            logger.error(
                "GET_SESSION_DATASET_FAILED",
                session_id=session_id,
                dataset_path=dataset_path,
                error=str(e),
            )
            return None

    # -- task listing --------------------------------------------------------

    def list_session_tasks(self, session_id: str) -> list[str]:
        """List task type names present in the session.

        Returns:
            E.g. ``["TRANSCRIPTION", "DIARIZATION"]``.
        """
        try:
            with self._open_file("r") as f:
                tasks_path = f"{SESSIONS_GROUP}/{session_id}/tasks"
                if tasks_path not in f:
                    return []

                task_types = list(f[tasks_path].keys())

                logger.debug(
                    "SESSION_TASKS_LISTED",
                    session_id=session_id,
                    task_count=len(task_types),
                )
                return task_types

        except Exception as e:
            logger.error(
                "LIST_SESSION_TASKS_FAILED",
                session_id=session_id,
                error=str(e),
            )
            return []
